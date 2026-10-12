#!/usr/bin/env python3
"""Intent parsing: a closed schema and a refusal of client deltas (task 2.4).

**Parsing returns its refusals; it does not raise them.**  See
:data:`server_v1_intent.IntentOutcome` for why, and note the consequence for
this file: every assertion below reads the returned value and asserts its type
*before* reading ``.code``.  Asserting the code first would pass on any object
that happened to carry one, which is exactly the check that let the raising
version of this module report 89 errors instead of one defect.
"""

from __future__ import annotations

import unittest

import harness  # noqa: F401  (path setup)
import server_v1_intent as intent_module
from server_v1_intent import (
    DELTA_KEYS,
    DELTA_MODIFIERS,
    INTENT_SCHEMAS,
    Intent,
    intent_from_json,
    parse_intent,
)
from server_v1_refusals import Refusal, RefusalCode

PLAYER = "00000000-0000-4000-8000-000000000001"


class RefusalAsserting(unittest.TestCase):
    """Assert the returned arm is a :class:`Refusal` with the expected code."""

    def assertRefusal(self, result: object, code: RefusalCode) -> Refusal:
        self.assertIsInstance(result, Refusal)
        self.assertIs(code, result.code)  # type: ignore[attr-defined]
        return result  # type: ignore[return-value]


class AcceptingTests(RefusalAsserting):
    def test_a_two_key_intent_is_accepted(self) -> None:
        parsed = parse_intent("collect", {"player_id": PLAYER, "row": 2})
        self.assertIsInstance(parsed, Intent)
        self.assertNotIsInstance(parsed, Refusal)
        self.assertEqual("collect", parsed.action)  # type: ignore[union-attr]
        self.assertEqual(PLAYER, parsed.player_id)  # type: ignore[union-attr]
        self.assertEqual(2, parsed.row)  # type: ignore[union-attr]

    def test_an_intent_is_frozen_and_carries_its_address(self) -> None:
        parsed = parse_intent("collect", {"player_id": PLAYER, "row": 7})
        assert isinstance(parsed, Intent)
        with self.assertRaises(Exception):
            parsed.row = 8  # type: ignore[misc]
        self.assertEqual("/maps/0/items/7", parsed.addressed_path())

    def test_row_zero_is_a_valid_address(self) -> None:
        # Zero is excluded in Python only for *falsy* checks; ``row=0`` must
        # still parse, and it must not be confused with "absent".
        parsed = parse_intent("collect", {"player_id": PLAYER, "row": 0})
        self.assertIsInstance(parsed, Intent)
        self.assertEqual(0, parsed.row)  # type: ignore[union-attr]

    def test_the_schema_is_exactly_two_keys(self) -> None:
        self.assertEqual(frozenset({"player_id", "row"}), INTENT_SCHEMAS["collect"])

    def test_the_two_arms_are_distinguishable(self) -> None:
        """The union is real: neither arm is a subclass of the other."""
        self.assertFalse(issubclass(Refusal, Intent))
        self.assertFalse(issubclass(Intent, Refusal))


class DeltaRefusalTests(RefusalAsserting):
    """Task 2.4: a request carrying an outcome is refused, not repaired."""

    def _assert_delta_refusal(self, body: dict, expected_field: str) -> None:
        refusal = self.assertRefusal(
            parse_intent("collect", body), RefusalCode.CLIENT_SUPPLIED_DELTA
        )
        self.assertEqual(400, refusal.http_status)
        self.assertEqual([expected_field], refusal.detail["delta_fields"])

    def test_every_stored_resource_name_is_a_delta_attempt(self) -> None:
        for name in ("xp", "gold", "wood", "oil", "steel", "cash", "mana"):
            with self.subTest(resource=name):
                self._assert_delta_refusal({"player_id": PLAYER, "row": 2, name: 5}, name)

    def test_the_legacy_vector_field_name_is_recognised(self) -> None:
        self._assert_delta_refusal(
            {"player_id": PLAYER, "row": 2, "resources_changed": [0, 1, 0, 1, 0, 0, 0, 0]},
            "resources_changed",
        )

    def test_health_damage_and_result_are_delta_attempts(self) -> None:
        for name in ("hp", "health", "damage", "result", "life", "experience", "exp"):
            with self.subTest(field=name):
                self._assert_delta_refusal({"player_id": PLAYER, "row": 2, name: 1}, name)

    def test_a_price_or_amount_is_a_delta_attempt(self) -> None:
        for name in ("amount", "price", "cost", "reward", "payout", "income"):
            with self.subTest(field=name):
                self._assert_delta_refusal({"player_id": PLAYER, "row": 2, name: 7}, name)

    def test_case_and_spelling_variants_are_recognised(self) -> None:
        # A bare-substring matcher was rejected while writing the module: it
        # would accuse "wooden_fence" of dictating an outcome.  These are the
        # cases that distinguishes the two designs.
        for key in ("Gold", "GOLD", "wood_delta", "resources_Changed", "Damage_Amount"):
            with self.subTest(key=key):
                self.assertRefusal(
                    parse_intent("collect", {"player_id": PLAYER, "row": 2, key: 1}),
                    RefusalCode.CLIENT_SUPPLIED_DELTA,
                )

    def test_a_key_that_only_contains_a_resource_word_is_not_a_delta(self) -> None:
        # The other direction of the same distinction: an over-broad matcher
        # would call this a delta attempt, and a false accusation is a worse
        # failure than an unrecognised key.
        for key in ("wooden_fence", "instant_cost_report", "my_gold_pick"):
            with self.subTest(key=key):
                self.assertRefusal(
                    parse_intent("collect", {"player_id": PLAYER, "row": 2, key: 1}),
                    RefusalCode.UNKNOWN_REQUEST_FIELD,
                )

    def test_every_declared_delta_key_is_recognised(self) -> None:
        """The vocabulary and the recogniser cannot drift apart."""
        for key in sorted(DELTA_KEYS):
            with self.subTest(key=key):
                self.assertRefusal(
                    parse_intent("collect", {"player_id": PLAYER, "row": 2, key: 1}),
                    RefusalCode.CLIENT_SUPPLIED_DELTA,
                )

    def test_a_delta_is_refused_before_an_unknown_key_is_reported(self) -> None:
        # Order matters for a client: "you tried to dictate an outcome" is the
        # security-relevant statement about the request.
        refusal = self.assertRefusal(
            parse_intent("collect", {"player_id": PLAYER, "row": 2, "wood": 1, "nonsense": 2}),
            RefusalCode.CLIENT_SUPPLIED_DELTA,
        )
        self.assertEqual(["wood"], refusal.detail["delta_fields"])

    def test_several_delta_fields_are_all_named(self) -> None:
        refusal = self.assertRefusal(
            parse_intent("collect", {"player_id": PLAYER, "row": 2, "wood": 1, "gold": 2}),
            RefusalCode.CLIENT_SUPPLIED_DELTA,
        )
        self.assertEqual(["gold", "wood"], refusal.detail["delta_fields"])
        self.assertEqual("gold", refusal.detail["refused_field"])


class DeltaModifierTests(RefusalAsserting):
    """A declared word qualified by a declared modifier, in either order.

    These pin the corrected rule's two directions over the **whole** vocabulary,
    so neither :data:`DELTA_KEYS` nor :data:`DELTA_MODIFIERS` can gain an entry
    the recogniser does not already honour.
    """

    def test_every_word_and_modifier_pair_is_recognised_in_both_orders(self) -> None:
        for word in sorted(DELTA_KEYS):
            for modifier in sorted(DELTA_MODIFIERS):
                for key in ("%s_%s" % (word, modifier), "%s_%s" % (modifier, word)):
                    with self.subTest(key=key):
                        self.assertRefusal(
                            parse_intent("collect", {"player_id": PLAYER, "row": 2, key: 1}),
                            RefusalCode.CLIENT_SUPPLIED_DELTA,
                        )

    def test_the_correction_counter_examples_are_unknown_fields(self) -> None:
        """The keys that motivated rejecting a substring match, pinned.

        Every one of these *contains* a declared delta word and none of them is
        that word qualified by a modifier, so none is a delta attempt.  The
        first three are named in the module's own docstring as the reason the
        bare-substring design was rejected; the test is what stops that
        rationale from drifting away from the implemented rule again.
        """
        for key in (
            "wooden_fence",
            "instant_cost_report",
            "instant_cost",
            "cost_of_war",
            "my_gold_pick",
            "my_gold",
            "gold_rich",
        ):
            with self.subTest(key=key):
                self.assertRefusal(
                    parse_intent("collect", {"player_id": PLAYER, "row": 2, key: 1}),
                    RefusalCode.UNKNOWN_REQUEST_FIELD,
                )

    def test_a_modifier_alone_is_still_a_delta_word_only_when_declared(self) -> None:
        """``amount`` is in both sets; ``value`` is in only the modifier set."""
        self.assertRefusal(
            parse_intent("collect", {"player_id": PLAYER, "row": 2, "amount": 1}),
            RefusalCode.CLIENT_SUPPLIED_DELTA,
        )
        self.assertRefusal(
            parse_intent("collect", {"player_id": PLAYER, "row": 2, "value": 1}),
            RefusalCode.UNKNOWN_REQUEST_FIELD,
        )


class UnknownFieldTests(RefusalAsserting):
    def test_an_extra_key_is_refused_rather_than_ignored(self) -> None:
        # v0 parses six envelope keys and discards five.  D3 rejects that shape.
        refusal = self.assertRefusal(
            parse_intent("collect", {"player_id": PLAYER, "row": 2, "ts": 12345}),
            RefusalCode.UNKNOWN_REQUEST_FIELD,
        )
        self.assertEqual(400, refusal.http_status)
        self.assertEqual(["ts"], refusal.detail["unknown_fields"])
        self.assertEqual(["player_id", "row"], refusal.detail["allowed_fields"])


class MalformedRequestTests(RefusalAsserting):
    def test_a_non_object_body_is_refused(self) -> None:
        for body in ([], "collect", 3, None, True):
            with self.subTest(body=body):
                self.assertRefusal(
                    parse_intent("collect", body), RefusalCode.MALFORMED_REQUEST
                )

    def test_a_missing_or_wrong_typed_required_key_is_refused(self) -> None:
        cases = (
            {"row": 2},
            {"player_id": PLAYER},
            {"player_id": "", "row": 2},
            {"player_id": 5, "row": 2},
            {"player_id": None, "row": 2},
            {"player_id": PLAYER, "row": "2"},
            {"player_id": PLAYER, "row": -1},
            {"player_id": PLAYER, "row": 1.5},
            {"player_id": PLAYER, "row": True},
        )
        for body in cases:
            with self.subTest(body=body):
                self.assertRefusal(
                    parse_intent("collect", body), RefusalCode.MALFORMED_REQUEST
                )

    def test_a_bool_row_is_refused_because_true_is_an_int(self) -> None:
        # Python's ``bool`` is an ``int``; without the explicit exclusion
        # ``row: true`` would address row 1.
        refusal = self.assertRefusal(
            parse_intent("collect", {"player_id": PLAYER, "row": True}),
            RefusalCode.MALFORMED_REQUEST,
        )
        self.assertEqual("bool", refusal.detail["received"])

    def test_an_unknown_action_is_refused_rather_than_matched_to_another(self) -> None:
        self.assertRefusal(
            parse_intent("expand", {"player_id": PLAYER, "row": 2}),
            RefusalCode.UNKNOWN_REQUEST_FIELD,
        )


class JsonDecodingTests(RefusalAsserting):
    """Decoding lives in the intent module, so the transport names no code."""

    def test_valid_json_is_parsed(self) -> None:
        raw = b'{"player_id": "%s", "row": 2}' % PLAYER.encode("ascii")
        parsed = intent_from_json("collect", raw)
        self.assertIsInstance(parsed, Intent)
        self.assertEqual(2, parsed.row)  # type: ignore[union-attr]

    def test_invalid_json_is_a_structural_refusal_not_a_crash(self) -> None:
        for raw in (b"", b"not json", b"{", b"[]", b'{"a": }'):
            with self.subTest(raw=raw):
                refusal = self.assertRefusal(
                    intent_from_json("collect", raw), RefusalCode.MALFORMED_REQUEST
                )
                self.assertEqual(400, refusal.http_status)

    def test_undecodable_bytes_are_a_structural_refusal(self) -> None:
        self.assertRefusal(
            intent_from_json("collect", b"\xff\xfe\x00bad"), RefusalCode.MALFORMED_REQUEST
        )

    def test_a_refused_body_never_leaks_a_balance(self) -> None:
        """No refusal detail anywhere in this module reports a balance value."""
        # Structural guarantee rather than a value check: the parser has no
        # access to a store at all, which is asserted by the invariant suite.
        self.assertFalse(hasattr(intent_module, "repository"))
        self.assertFalse(hasattr(intent_module, "content"))


if __name__ == "__main__":
    unittest.main()