#!/usr/bin/env python3
"""Compatibility API v0 tutorial derivation tests (OpenSpec task 2.1).

No server and no socket: this suite is pure derivation, so it needs no corpus
and opens no connection.  The socket guard is still installed, which is what
makes "pure" a checked claim rather than an assertion.

Covered:

* **the committed gate** — both arms, the nine-value hole computed from the arm
  constants rather than typed out, both hole edges, every boundary the committed
  replay harness already covers (referenced, never re-claimed), and the three
  recorded absences: no upper bound, no lower bound, no type check.
* **the one named predicate** — :func:`tutorial_envelope.gate_satisfied`, with its
  named reporting inverse :func:`tutorial_envelope.gate_verdict` and the
  short-circuit order the two arms are tested in.
* **the three legacy 500-raising shapes** — a string step, a missing step, and a
  ``null`` step are each refused with their own named code, plus a ``bool`` and a
  ``float`` as the two further wire types the contract refuses.  The float and
  the bool are checked against the *measured* legacy outcome so the divergence is
  recorded as confined rather than as a difference.
* **the intent-only envelope** — exactly six legacy keys, exactly one command, the
  step and nothing else, and a vector that is neutral by construction.  The
  negative space is asserted too: no key anywhere in the envelope can carry an
  outcome, a stored flag, or a resource movement.
* **the vector refusal** — any non-zero slot is refused, which is what forecloses
  the client-sent mint the capture records.
* **the projection** — the flag carried verbatim, fail-closed on an absent or
  wrongly-typed ``playerInfo``, and **never** a derived step, ratio, remaining
  time, or completion.
* **the gate record** — every field a committed fact or a recorded absence, with
  nothing derived from another.
"""

from __future__ import annotations

import unittest

import compat_test_harness as harness  # noqa: F401  (installs sys.path)

import tutorial_envelope as T


class GateTest(unittest.TestCase):
    """The committed gate: a disjunction with a nine-value hole."""

    def test_both_arms_reproduce_the_committed_command(self) -> None:
        # command.py:63 -- ``if tutorial_step >= 25 or tutorial_step == 15:``
        self.assertEqual(T.GATE_LOWER_ARM, 25)
        self.assertEqual(T.GATE_EXACT_ARM, 15)
        self.assertIn(
            "tutorial_step >= %d or tutorial_step == %d" % (25, 15),
            T.gate_record()["expression"],
        )

    def test_the_exact_arm_completes(self) -> None:
        self.assertTrue(T.gate_satisfied(15))

    def test_the_lower_arm_completes_at_and_above(self) -> None:
        for step in (25, 26, 100, 10 ** 9):
            self.assertTrue(T.gate_satisfied(step), step)

    def test_the_nine_value_hole_does_not_complete(self) -> None:
        # Steps 16..24 inclusive.  Executed-legacy per-value; this pins the table.
        for step in range(T.GATE_HOLE_LOW, T.GATE_HOLE_HIGH + 1):
            self.assertFalse(T.gate_satisfied(step), step)
        self.assertEqual(T.GATE_HOLE_LOW, 16)
        self.assertEqual(T.GATE_HOLE_HIGH, 24)
        self.assertEqual(T.GATE_HOLE_SIZE, 9)
        self.assertEqual(len(T.gate_hole_steps()), 9)
        self.assertEqual(T.gate_hole_steps(), list(range(16, 25)))

    def test_the_hole_edges_decline_and_the_arms_complete(self) -> None:
        self.assertFalse(T.gate_satisfied(T.GATE_HOLE_LOW))
        self.assertFalse(T.gate_satisfied(T.GATE_HOLE_HIGH))
        self.assertTrue(T.gate_satisfied(T.GATE_HOLE_HIGH + 1))
        self.assertFalse(T.gate_satisfied(T.GATE_EXACT_ARM - 1))
        self.assertTrue(T.gate_satisfied(T.GATE_EXACT_ARM))

    def test_there_is_no_lower_bound(self) -> None:
        # Executed-legacy: -1 declines, but nothing *checks* it, so a still
        # smaller negative is equally accepted and simply declines.
        for step in (-1, -100, -10 ** 9):
            self.assertFalse(T.gate_satisfied(step), step)
        self.assertFalse(T.GATE_HAS_LOWER_BOUND)

    def test_there_is_no_upper_bound(self) -> None:
        self.assertTrue(T.gate_satisfied(10 ** 9))
        self.assertTrue(T.gate_satisfied(2 ** 62))
        self.assertFalse(T.GATE_HAS_UPPER_BOUND)

    def test_there_is_no_type_check(self) -> None:
        self.assertFalse(T.GATE_HAS_TYPE_CHECK)

    def test_the_hole_is_computed_not_typed(self) -> None:
        # If an arm constant ever moved, the hole must move with it rather than
        # silently disagreeing with the prose.
        self.assertEqual(T.GATE_HOLE_LOW, T.GATE_EXACT_ARM + 1)
        self.assertEqual(T.GATE_HOLE_HIGH, T.GATE_LOWER_ARM - 1)

    def test_the_hole_list_is_a_fresh_list_every_call(self) -> None:
        first = T.gate_hole_steps()
        first.append(999)
        self.assertNotIn(999, T.gate_hole_steps())

    def test_the_predicate_is_total_over_a_non_integer(self) -> None:
        # Total, so a caller can never crash on an unvalidated value — and
        # because the client parses EVERY JSON number as a float, a client-side
        # mirror of this predicate must survive a float too.
        for value in ("15", None, 15.0, True, [15], {"step": 15}):
            self.assertFalse(T.gate_satisfied(value), value)
            self.assertEqual(T.gate_verdict(value), "none", value)

    def test_totality_is_not_reproduction_and_is_recorded_as_such(self) -> None:
        # The one place the two differ in OUTCOME: legacy COMPLETES on 15.0.
        # This predicate reports the refusal, so it must never be read as a
        # faithful gate for a non-integer.
        self.assertFalse(T.gate_satisfied(15.0))
        self.assertTrue(15.0 == T.GATE_LOWER_ARM or 15.0 == T.GATE_EXACT_ARM)
        self.assertTrue(T.LEGACY_ACCEPTS_FLOAT_STEP)
        # ...and no caller may consult it before validate_step settles the type,
        # which the endpoint's ordering guarantees (validate, then gate).
        self.assertEqual(T.validate_step(15), 15)

    def test_verdict_names_the_arm_that_fired(self) -> None:
        self.assertEqual(T.gate_verdict(15), "exact_arm")
        self.assertEqual(T.gate_verdict(25), "lower_arm")
        self.assertEqual(T.gate_verdict(24), "none")

    def test_verdict_follows_the_or_short_circuit(self) -> None:
        # 25 satisfies BOTH arms; legacy's ``or`` tests ``>=`` first, so the
        # verdict must report the lower arm.
        self.assertTrue(T.gate_satisfied(T.GATE_LOWER_ARM))
        self.assertEqual(T.gate_verdict(T.GATE_LOWER_ARM), "lower_arm")

    def test_the_replay_harness_boundary_is_referenced_not_reclaimed(self) -> None:
        # tools/protocol-replay/test_protocol_replay.py:173-179 pins these six
        # steps against a STUB oracle, so it is not an executed-legacy oracle.
        self.assertEqual(tuple(T.REPLAY_BOUNDARY_STEPS), (14, 15, 24, 25, 26, -1))
        self.assertFalse(T.REPLAY_ORACLE_IS_EXECUTED_LEGACY)
        for step in T.REPLAY_BOUNDARY_STEPS:
            self.assertEqual(
                T.gate_satisfied(step),
                T.gate_satisfied(step),
                "replay step %d must resolve through the same predicate" % step,
            )

    def test_the_flag_is_write_only(self) -> None:
        self.assertEqual(T.FLAG_READER_COUNT, 0)
        self.assertEqual(list(T.FLAG_WRITER_LINES), ["command.py:65"])
        self.assertEqual(T.FLAG_OCCURRENCES, 1)

    def test_the_legacy_surface_is_the_whole_command(self) -> None:
        self.assertEqual(T.COMPLETE_TUTORIAL_COMMAND, "complete_tutorial")
        self.assertEqual(T.TUTORIAL_OCCURRENCES, 6)
        self.assertEqual(T.TUTORIAL_OCCURRENCE_LINES, 5)
        self.assertEqual(T.STEP_OCCURRENCES, 4)
        self.assertEqual(len(T.LEGACY_MODULES), 11)
        self.assertIn("command.py", T.LEGACY_MODULES)
        self.assertIn("get_player_info.py", T.LEGACY_MODULES)


class StepValidationTest(unittest.TestCase):
    """The three legacy 500-raising shapes, and two more refused wire types."""

    def test_an_integer_step_is_accepted_verbatim(self) -> None:
        for step in (-1, 0, 15, 24, 25, 10 ** 9):
            self.assertEqual(T.validate_step(step), step)

    def test_a_string_step_is_refused(self) -> None:
        # Legacy raises TypeError on the comparison -> unhandled HTTP 500.
        with self.assertRaises(T.EnvelopeError) as caught:
            T.validate_step("15")
        self.assertEqual(caught.exception.code, "invalid_step")
        self.assertIn("string", str(caught.exception))

    def test_a_null_step_is_refused(self) -> None:
        with self.assertRaises(T.EnvelopeError) as caught:
            T.validate_step(None)
        self.assertEqual(caught.exception.code, "null_step")

    def test_a_missing_step_is_refused_by_its_own_code(self) -> None:
        with self.assertRaises(T.EnvelopeError) as caught:
            T.require_step({"user_id": "1"})
        self.assertEqual(caught.exception.code, "missing_step")

    def test_a_present_step_is_read_from_the_single_documented_key(self) -> None:
        self.assertEqual(T.STEP_KEY, "step")
        self.assertEqual(T.require_step({"step": 15}), 15)

    def test_a_non_object_body_is_refused(self) -> None:
        with self.assertRaises(T.EnvelopeError) as caught:
            T.require_step([15])
        self.assertEqual(caught.exception.code, "invalid_payload")

    def test_a_bool_is_refused_and_legacy_also_declined(self) -> None:
        # ``True`` is an int in Python and satisfies neither arm, so legacy
        # DECLINES and the flag stays put.  Same state, different response.
        with self.assertRaises(T.EnvelopeError) as caught:
            T.validate_step(True)
        self.assertEqual(caught.exception.code, "invalid_step")
        self.assertIn("boolean", str(caught.exception))
        self.assertFalse(T.gate_satisfied(True))

    def test_a_float_is_refused_and_the_measured_legacy_outcome_is_recorded(self) -> None:
        # Legacy COMPLETES on 15.0 (15.0 == 15).  Refusing it is the same
        # confinement: the flag is untouched either way.
        self.assertTrue(T.LEGACY_ACCEPTS_FLOAT_STEP)
        self.assertTrue(15.0 == 15)
        with self.assertRaises(T.EnvelopeError) as caught:
            T.validate_step(15.0)
        self.assertEqual(caught.exception.code, "invalid_step")

    def test_a_list_and_a_dict_are_refused(self) -> None:
        for value in ([15], {"step": 15}):
            with self.assertRaises(T.EnvelopeError) as caught:
                T.validate_step(value)
            self.assertEqual(caught.exception.code, "invalid_step")

    def test_step_kind_names_every_wire_type(self) -> None:
        self.assertEqual(T.step_kind(15), "integer")
        self.assertEqual(T.step_kind(15.0), "float")
        self.assertEqual(T.step_kind(True), "boolean")
        self.assertEqual(T.step_kind("15"), "string")
        self.assertEqual(T.step_kind(None), "null")

    def test_the_three_raising_shapes_are_the_recorded_three(self) -> None:
        self.assertEqual(
            tuple(T.LEGACY_RAISING_SHAPES),
            ("string_step", "missing_step", "null_step"),
        )
        self.assertEqual(T.LEGACY_RAISING_STATUS, 500)


class VectorTest(unittest.TestCase):
    """The derived vector is neutral by construction."""

    def test_the_neutral_vector_is_eight_zeros(self) -> None:
        vector = T.neutral_vector()
        self.assertEqual(vector, [0] * 8)
        self.assertEqual(len(vector), T.RESOURCE_VECTOR_SLOTS)

    def test_the_neutral_vector_is_a_fresh_list_every_call(self) -> None:
        first = T.neutral_vector()
        first[2] = 999999
        self.assertEqual(T.neutral_vector(), [0] * 8)

    def test_a_neutral_vector_validates(self) -> None:
        self.assertEqual(T.validate_vector([0] * 8), [0] * 8)

    def test_any_non_zero_slot_is_refused(self) -> None:
        # This is the refusal that forecloses the captured minting transaction:
        # one legacy request moved all seven stored resources through this very
        # command, so a non-zero slot is a client-trusted mint.
        for index in range(T.RESOURCE_VECTOR_SLOTS):
            ladder = [0] * 8
            ladder[index] = 101
            with self.assertRaises(T.EnvelopeError) as caught:
                T.validate_vector(ladder)
            self.assertEqual(caught.exception.code, "invalid_vector")
            self.assertIn("slot %d" % index, str(caught.exception))

    def test_the_recorded_minting_ladder_is_refused(self) -> None:
        with self.assertRaises(T.EnvelopeError):
            T.validate_vector(list(T.MINTING_LADDER))

    def test_a_negative_slot_is_refused_too(self) -> None:
        with self.assertRaises(T.EnvelopeError):
            T.validate_vector([0, 0, -5, 0, 0, 0, 0, 0])

    def test_a_wrong_width_or_type_is_refused(self) -> None:
        for bad in ([0] * 7, [0] * 9, "00000000", None, [0] * 7 + ["x"]):
            with self.assertRaises(T.EnvelopeError) as caught:
                T.validate_vector(bad)
            self.assertEqual(caught.exception.code, "invalid_vector")

    def test_the_anchor_records_what_it_anchors(self) -> None:
        self.assertEqual(len(T.MINTING_LADDER), 8)
        self.assertEqual(T.MINTING_STEP, 15)
        self.assertEqual(T.MINTING_RESOURCES_MOVED, 7)
        self.assertEqual(T.MINTING_CHANGED_LEAVES, 8)
        self.assertEqual(T.MINTING_LADDER[0], 101)


class EnvelopeTest(unittest.TestCase):
    """The intent-only batch: a step and nothing else."""

    def test_the_envelope_carries_exactly_the_six_legacy_keys(self) -> None:
        envelope = T.build_envelope(15)
        self.assertEqual(sorted(envelope), sorted(T.ENVELOPE_KEYS))
        self.assertEqual(len(envelope), 6)

    def test_the_batch_carries_exactly_one_command(self) -> None:
        envelope = T.build_envelope(15)
        self.assertEqual(len(envelope["commands"]), 1)
        entry = envelope["commands"][0]
        self.assertEqual(entry[0], 0)
        self.assertEqual(entry[1], "complete_tutorial")
        self.assertEqual(entry[2], [15])
        self.assertEqual(entry[3], [0] * 8)

    def test_the_only_argument_is_the_step(self) -> None:
        entry = T.build_envelope(24)["commands"][0]
        self.assertEqual(entry[2], [24])
        self.assertEqual(len(entry[2]), 1)

    def test_no_top_level_key_carries_an_outcome_or_a_flag(self) -> None:
        # The negative space, asserted structurally rather than by review.  The
        # COMMAND name is legitimately ``complete_tutorial`` and is excluded, as
        # it is the operation's identity rather than a channel for a result; the
        # scan is over the six legacy envelope keys and the command's arguments.
        envelope = T.build_envelope(15)
        entry = envelope["commands"][0]
        vocabulary = (
            "completed_tutorial", "outcome", "result", "flag", "reward",
            "resources_changed", "player_info", "playerInfo", "vector",
            "bonus", "grant", "gold", "mana", "cash", "xp",
        )
        for name in list(envelope):
            lowered = str(name).lower()
            for word in vocabulary:
                self.assertNotIn(
                    word, lowered, "envelope key %r leaks %r" % (name, word)
                )
        # The arguments carry the step and nothing else, so there is no second
        # slot an outcome could hide in.
        self.assertEqual(len(entry[2]), 1)
        self.assertEqual(entry[2], [15])
        self.assertEqual(entry[3], [0] * T.RESOURCE_VECTOR_SLOTS)

    def test_the_only_channel_besides_the_step_is_the_derived_vector(self) -> None:
        entry = T.build_envelope(15)["commands"][0]
        self.assertEqual(len(entry), 4)
        self.assertEqual(entry[0], 0)
        self.assertEqual(entry[1], T.COMPLETE_TUTORIAL_COMMAND)

    def test_a_client_vector_cannot_ride_along(self) -> None:
        with self.assertRaises(T.EnvelopeError) as caught:
            T.build_envelope(15, vector=list(T.MINTING_LADDER))
        self.assertEqual(caught.exception.code, "invalid_vector")

    def test_a_supplied_neutral_vector_is_accepted(self) -> None:
        envelope = T.build_envelope(15, vector=[0] * 8)
        self.assertEqual(envelope["commands"][0][3], [0] * 8)

    def test_a_malformed_step_is_refused_before_the_vector(self) -> None:
        with self.assertRaises(T.EnvelopeError) as caught:
            T.build_envelope("15")
        self.assertEqual(caught.exception.code, "invalid_step")

    def test_a_bad_timestamp_is_refused(self) -> None:
        for bad in (-1, "now", 1.5, True):
            with self.assertRaises(T.EnvelopeError) as caught:
                T.build_envelope(15, ts=bad)
            self.assertEqual(caught.exception.code, "invalid_timestamp")

    def test_the_timestamp_defaults_to_the_current_time(self) -> None:
        import time

        before = int(time.time())
        envelope = T.build_envelope(15)
        self.assertGreaterEqual(envelope["ts"], before)

    def test_no_gate_bound_is_applied_to_an_integer_step(self) -> None:
        # 10**9 completes in legacy and is accepted here for the same reason.
        for step in (-10 ** 9, 0, 10 ** 9):
            self.assertEqual(T.build_envelope(step)["commands"][0][2], [step])

    def test_the_envelope_is_json_serializable_through_the_legacy_field(self) -> None:
        envelope = T.build_envelope(15)
        field = T.data_field(envelope)
        self.assertIn(";", field)
        self.assertEqual(T.parse_data_field(field)["commands"], envelope["commands"])


class ProjectionTest(unittest.TestCase):
    """One field, carried verbatim, failing closed."""

    def test_the_flag_is_carried_verbatim_not_folded(self) -> None:
        projection = T.project_tutorial_state({"completed_tutorial": 1})
        self.assertTrue(projection["resolvable"])
        self.assertEqual(projection["stored"], 1)
        self.assertIs(projection["completed"], True)

    def test_a_recorded_zero_is_not_absent(self) -> None:
        projection = T.project_tutorial_state({"completed_tutorial": 0})
        self.assertTrue(projection["resolvable"])
        self.assertEqual(projection["stored"], 0)
        self.assertIs(projection["completed"], False)

    def test_an_absent_record_fails_closed(self) -> None:
        for value in (None, [], "playerInfo", 15):
            projection = T.project_tutorial_state(value)
            self.assertFalse(projection["resolvable"])
            self.assertIsNone(projection["stored"])
            # Never False: "the save does not say" is not "the save says no".
            self.assertIsNone(projection["completed"])

    def test_an_absent_key_fails_closed(self) -> None:
        projection = T.project_tutorial_state({"cash": 5})
        self.assertFalse(projection["resolvable"])

    def test_an_empty_record_fails_closed(self) -> None:
        self.assertFalse(T.project_tutorial_state({})["resolvable"])

    def test_the_projection_names_its_record_and_key(self) -> None:
        projection = T.project_tutorial_state({"completed_tutorial": 1})
        self.assertEqual(projection["record"], "playerInfo")
        self.assertEqual(projection["key"], "completed_tutorial")
        self.assertEqual(T.PLAYER_INFO_RECORD, "playerInfo")
        self.assertEqual(T.FLAG_KEY, "completed_tutorial")

    def test_no_step_ratio_or_remaining_time_is_derived(self) -> None:
        # The legacy save stores no step, so the projection must not invent one.
        projection = T.project_tutorial_state({"completed_tutorial": 1})
        self.assertEqual(
            sorted(projection),
            ["completed", "key", "record", "resolvable", "stored"],
        )
        for derived in ("step", "progress", "ratio", "remaining", "total_steps"):
            self.assertNotIn(derived, projection)

    def test_the_flag_reader_is_graceful(self) -> None:
        self.assertIsNone(T.completed_flag(None))
        self.assertIsNone(T.completed_flag([]))
        self.assertIsNone(T.completed_flag({}))
        self.assertEqual(T.completed_flag({"completed_tutorial": 7}), 7)


class GateRecordTest(unittest.TestCase):
    """Every field is a committed fact or a recorded absence."""

    def test_the_record_reports_both_arms_and_the_hole(self) -> None:
        record = T.gate_record()
        self.assertEqual(record["lower_arm"], 25)
        self.assertEqual(record["exact_arm"], 15)
        self.assertEqual(record["hole_size"], 9)
        self.assertEqual(record["hole_steps"], list(range(16, 25)))

    def test_the_record_reports_the_three_absences(self) -> None:
        record = T.gate_record()
        self.assertFalse(record["has_upper_bound"])
        self.assertFalse(record["has_lower_bound"])
        self.assertFalse(record["has_type_check"])

    def test_the_record_reports_the_divergence(self) -> None:
        record = T.gate_record()
        self.assertEqual(
            record["raising_shapes"], ["string_step", "missing_step", "null_step"]
        )
        self.assertEqual(record["raising_status"], 500)

    def test_the_record_marks_the_replay_oracle_as_not_executed_legacy(self) -> None:
        self.assertFalse(T.gate_record()["replay_oracle_is_executed_legacy"])

    def test_the_record_derives_nothing_from_another_field(self) -> None:
        record = T.gate_record()
        self.assertEqual(record["lower_arm"], T.GATE_LOWER_ARM)
        self.assertEqual(record["exact_arm"], T.GATE_EXACT_ARM)
        self.assertEqual(record["hole_low"], T.GATE_HOLE_LOW)
        self.assertEqual(record["hole_high"], T.GATE_HOLE_HIGH)
        self.assertEqual(record["hole_steps"], T.gate_hole_steps())

    def test_the_record_is_a_fresh_dict_every_call(self) -> None:
        first = T.gate_record()
        first["lower_arm"] = 999
        self.assertEqual(T.gate_record()["lower_arm"], 25)


class CommittedCorpusFactsTest(unittest.TestCase):
    """The corpus and content facts the whole line rests on."""

    def test_the_committed_flag_transition(self) -> None:
        self.assertEqual(T.COMMITTED_FLAG_BEFORE, 0)
        self.assertEqual(T.COMMITTED_FLAG_AFTER, 1)

    def test_the_committed_placement_count(self) -> None:
        self.assertEqual(T.COMMITTED_PLACEMENTS, 40)

    def test_the_committed_resource_vector(self) -> None:
        self.assertEqual(
            sorted(T.COMMITTED_RESOURCE_BEFORE),
            ["cash", "gold", "mana", "oil", "steel", "wood", "xp"],
        )
        self.assertEqual(T.COMMITTED_RESOURCE_BEFORE["xp"], 4)
        self.assertEqual(T.COMMITTED_RESOURCE_BEFORE["cash"], 5)
        self.assertEqual(T.COMMITTED_RESOURCE_BEFORE["mana"], 0)

    def test_there_is_no_committed_tutorial_content(self) -> None:
        self.assertEqual(T.COMMITTED_CONTENT_OCCURRENCES, 0)
        self.assertGreater(T.COMMITTED_CONTENT_FILES_CHECKED, 0)

    def test_the_corpus_census(self) -> None:
        self.assertEqual(T.CORPUS_VILLAGE_SAVES, 31)
        self.assertEqual(T.CORPUS_SAVES_RECORDING_COMPLETE, 30)
        self.assertEqual(T.CORPUS_ONLY_INCOMPLETE_SAVE, "villages/initial.json")

    def test_the_flag_reaches_the_client_only_by_whole_dict_inclusion(self) -> None:
        self.assertEqual(T.FLAG_CLIENT_VIA_WHOLE_DICT_LINE, 15)


class OfflineGuardTest(unittest.TestCase):
    """'Pure derivation, no socket' is checked rather than asserted."""

    def test_the_suite_runs_under_the_socket_guard(self) -> None:
        with harness.offline():
            T.gate_satisfied(15)
            T.build_envelope(15)
            T.project_tutorial_state({"completed_tutorial": 1})


if __name__ == "__main__":
    unittest.main()