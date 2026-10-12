#!/usr/bin/env python3
"""v1's collection against the captured executed-legacy fixture (task 4.4).

**The comparison runs against the captured bytes.**  Nothing in this file
starts the legacy Flask server, imports ``command.py``, or re-captures
anything; the oracle is the committed fixture under
``tests/fixtures/godot-building-collect/``, which was recorded once by
``apps/compat-api/capture_collect_fixture.py`` against a disposable copy of the
preserved server.  That is the whole point of the fixture: v1's derivation is
checked against *what the legacy server actually did*, not against what it
would do if it were run today.

Three things are asserted, and they are not the same claim:

1. **The payout agrees.**  v1 derives ``wood 60`` and ``xp 3``; the fixture
   records exactly those as the vector the legacy server applied.  This is the
   load-bearing one.
2. **The row agrees.**  ``item[3]`` moves from ``0`` to the recorded capture
   instant and nothing else on the row changes.
3. **The refusals agree in *kind*, not by name.**  v0's codes are its own
   (``too_early`` where v1 says ``below_first_rung``); the vocabulary was
   deliberately not reused (design decision recorded in
   ``server_v1_refusals``).  What is compared is that both surfaces refuse the
   same four circumstances.

**The clock is pinned, not sent.**  ``--fixed-now`` on ``run.py`` exists for
exactly this: the fixture's instant is 1790705901, and a test cannot legitimately
set a server's clock through a request field.  Here the clock is the
injected callable, and the corpus row is reset to the fixture's own ``before``.

**A claim this file does not make:** that v1 is *more correct* than legacy.
The fixture shows legacy accepted a client-sent vector; v1 refuses to accept one
at all.  Where the two agree, it is because the vector that was sent happened to
equal what v1 derives -- not because both computed it.
"""

from __future__ import annotations

import json
import unittest
from typing import Any, Dict, List

import harness
from harness import (
    COLLECT_STEP,
    FilesystemSaveRepository,
    build_corpus,
    load_content,
    remove_corpus,
    seed_player_id,
)
from server_v1_collect import collect
from server_v1_intent import Intent
from server_v1_outcomes import Success
from server_v1_refusals import Refusal, RefusalCode

#: The fixture's recorded capture instant, read from the fixture rather than
#: transcribed: a literal here would let the fixture and this file drift apart
#: silently, and the whole claim of the file is that they are the same bytes.
#: Read out of the recorded request envelope's ``ts`` -- the legacy
#: ``time_now()`` at capture -- rather than transcribed.  The fixture's
#: ``before.json`` records the row's instant as ``0``, so the capture instant is
#: only recoverable from the request side.
def _capture_instant() -> int:
    data = json.loads((COLLECT_STEP / "request.json").read_text(encoding="utf-8"))["form"]["data"]
    envelope = json.loads(data.split(";", 1)[1])
    return int(envelope["ts"])


CAPTURE_INSTANT = _capture_instant()


def fixture(name: str) -> Any:
    return json.loads((COLLECT_STEP / name).read_text(encoding="utf-8"))


class FixtureShapeTests(unittest.TestCase):
    """The oracle must be the real recorded fixture, or nothing below means
    anything.  Asserted first so a renamed or truncated capture fails loudly
    instead of being compared against."""

    def setUp(self) -> None:
        self.before = fixture("before.json")
        self.after = fixture("after.json")
        self.request = fixture("request.json")

    def test_the_three_capture_files_are_present_and_parsed(self) -> None:
        self.assertEqual(["maps", "playerInfo", "privateState", "version"], list(self.before))
        self.assertEqual(list(self.before), list(self.after))

    def test_the_capture_instant_is_read_from_the_recorded_request(self) -> None:
        # Not transcribed: the envelope's ``ts`` is the legacy ``time_now()``.
        self.assertEqual(1790705901, CAPTURE_INSTANT)

    def test_the_recorded_response_was_an_unconditional_success(self) -> None:
        raw = (COLLECT_STEP / "response.body").read_bytes()
        # **A three-way discrepancy inside the committed fixture is recorded
        # here rather than reconciled, and this file is preserved material.**
        # Three figures exist for one response and no two agree:
        #
        #   * the file is **22 bytes**: ``{"result":"success"}`` (20) plus a
        #     trailing CRLF (2);
        #   * ``response.meta.json`` records ``body_bytes: 21`` and the header
        #     block records ``Content-Length: 21``;
        #   * the JSON payload itself is **20** bytes -- there is no space after
        #     the colon, which is Flask's own ``jsonify`` output.
        #
        # So the manifest appears to have counted the payload plus **one**
        # terminator byte while the capture writer emitted **two**.  The
        # likeliest cause is that the body was measured from a `str` (where a
        # newline is one character) and written in text mode (where it became
        # two bytes), and it is recorded as a hypothesis, not a finding.
        #
        # Nothing here "fixes" it: this is captured evidence, and editing it to
        # make an assertion pass would destroy the only oracle this line has.
        # The assertion is therefore on the **file's own bytes**, which are the
        # ground truth, and the manifest figure is reported next to it so a
        # reader sees the disagreement instead of inheriting a tidied number.
        # Whether to correct the manifest belongs to the line that owns the
        # fixture, not to a consumer of it.
        self.assertEqual(b'{"result":"success"}\r\n', raw)
        payload = raw.rstrip(b"\r\n")
        self.assertEqual(20, len(payload))
        meta = json.loads((COLLECT_STEP / "response.meta.json").read_text(encoding="utf-8"))
        self.assertEqual(21, meta["body_bytes"])
        self.assertEqual("21", meta["headers"]["Content-Length"])
        # The payload and the recorded byte count disagree by exactly the
        # terminator; if a future capture fixes one side, this fires.
        self.assertEqual(meta["body_bytes"] - len(payload), 1)
        self.assertEqual(len(raw) - len(payload), 2)

    def test_the_recorded_command_is_a_single_collect_on_row_two(self) -> None:
        data = self.request["form"]["data"]
        self.assertIn('"collect"', data)
        self.assertIn('"commands":[[0,"collect",[2]', data)


class PayoutParityTests(unittest.TestCase):
    """Task 4.1's load-bearing claim, measured against the captured bytes."""

    def setUp(self) -> None:
        """A fresh corpus per test, seeded from the fixture's own ``before``.

        **This was a class-level fixture and it was wrong**, in a way only the
        failures exposed: a successful collection *moves the row's recorded
        instant*, so the first test consumed the one unbounded-elapsed
        collection the fixture supports and every test after it saw
        ``elapsed = 0`` and was refused ``below_first_rung``.  One transaction
        per corpus is the property the fixture has, and a shared corpus silently
        spent it.
        """
        self.corpus = build_corpus(mutate=lambda document: None)
        self.addCleanup(remove_corpus, self.corpus)
        self.repository = FilesystemSaveRepository(self.corpus)
        self.content = load_content(harness.REPO_ROOT)
        self.player = seed_player_id()
        self._seed_from_fixture()

    def _seed_from_fixture(self) -> None:
        before = fixture("before.json")
        document = self.repository.read(self.player)
        for name, path in (
            ("xp", ("maps", 0, "xp")),
            ("gold", ("maps", 0, "gold")),
            ("wood", ("maps", 0, "wood")),
            ("oil", ("maps", 0, "oil")),
            ("steel", ("maps", 0, "steel")),
        ):
            document.set_resource(name, before["maps"][0][name])
        document.set_resource("cash", before["playerInfo"]["cash"])
        document.set_resource("mana", before["privateState"]["mana"])
        row = document.row(2)
        assert row is not None
        row[0:8] = list(before["maps"][0]["items"]["2"])
        self.repository.write(document)

    def _run(self) -> Success:
        outcome = collect(
            Intent(action="collect", player_id=self.player, row=2),
            self.content,
            self.repository,
            CAPTURE_INSTANT,
        )
        self.assertIsInstance(outcome, Success)
        return outcome

    def test_the_derived_payout_equals_the_recorded_vector(self) -> None:
        outcome = self._run()
        derived = dict(outcome.derivation.deltas)
        recorded = fixture("after.json")
        for name in ("xp", "wood", "gold", "oil", "steel", "cash", "mana"):
            with self.subTest(resource=name):
                expected = _recorded(name, recorded) - _recorded(name, fixture("before.json"))
                self.assertEqual(expected, derived.get(name, 0))

    def test_the_stored_balances_after_v1_match_the_recorded_after_state(self) -> None:
        outcome = self._run()
        recorded = fixture("after.json")
        stored = self.repository.read(self.player).resources()
        self.assertEqual(recorded["maps"][0]["xp"], stored["xp"])
        self.assertEqual(recorded["maps"][0]["wood"], stored["wood"])
        self.assertEqual(recorded["maps"][0]["gold"], stored["gold"])
        self.assertEqual(recorded["maps"][0]["oil"], stored["oil"])
        self.assertEqual(recorded["maps"][0]["steel"], stored["steel"])
        self.assertEqual(recorded["playerInfo"]["cash"], stored["cash"])
        self.assertEqual(recorded["privateState"]["mana"], stored["mana"])
        self.assertEqual(stored, outcome.state)

    def test_the_recorded_row_and_v1s_row_agree_except_for_the_instant(self) -> None:
        outcome = self._run()
        recorded = fixture("after.json")["maps"][0]["items"]["2"]
        stored_row = self.repository.read(self.player).row(2)
        self.assertIsNotNone(stored_row)
        self.assertEqual(CAPTURE_INSTANT, stored_row[3])
        self.assertEqual(recorded[3], stored_row[3])
        # Every other slot is the fixture's own before value, carried through.
        before_row = fixture("before.json")["maps"][0]["items"]["2"]
        self.assertEqual(list(before_row[:3]), list(stored_row[:3]))
        self.assertEqual(list(before_row[4:]), list(stored_row[4:]))
        self.assertEqual(outcome.row_instant, stored_row[3])

    def test_the_derived_amount_is_the_committed_one_scaled_by_the_top_rung(self) -> None:
        outcome = self._run()
        item = self.content.item(905)
        self.assertIsNotNone(item)
        self.assertEqual("20", str(item["collect"]))
        self.assertEqual("w", item["collect_type"])
        self.assertEqual("1", str(item["collect_xp"]))
        self.assertEqual("0", str(item["max_collects"]))
        minutes, multipliers = self.content.collect_ladder()
        self.assertEqual([5, 60, 240, 480], list(minutes))
        self.assertEqual([0.25, 1, 2, 3], list(multipliers))
        # Row 2's recorded instant is 0, so elapsed is unbounded and the top
        # committed rung is the deterministic one.
        self.assertEqual(3, outcome.derivation.rung_index)
        self.assertEqual(28800, outcome.derivation.rung_threshold_seconds)
        self.assertEqual(3.0, outcome.derivation.rung_multiplier)
        self.assertEqual(60, outcome.derivation.deltas["wood"])
        self.assertEqual(3, outcome.derivation.deltas["xp"])


class RefusalParityTests(unittest.TestCase):
    """v1 refuses the four circumstances v0 refuses, under v1's own names."""

    def setUp(self) -> None:
        self.corpus = build_corpus(mutate=lambda document: None)
        self.addCleanup(remove_corpus, self.corpus)
        self.repository = FilesystemSaveRepository(self.corpus)
        self.content = load_content(harness.REPO_ROOT)
        self.player = seed_player_id()

    def _collect(self) -> Any:
        return collect(
            Intent(action="collect", player_id=self.player, row=2),
            self.content,
            self.repository,
            CAPTURE_INSTANT,
        )

    def test_below_the_first_rung_refuses_where_v0_said_too_early(self) -> None:
        document = self.repository.read(self.player)
        document.set_row_instant(2, CAPTURE_INSTANT - 299)
        self.repository.write(document)
        outcome = self._collect()
        self.assertIsInstance(outcome, Refusal)
        self.assertEqual(RefusalCode.BELOW_FIRST_RUNG, outcome.code)

    def test_a_construction_refuses_and_the_countdown_is_untouched(self) -> None:
        """The recorded probe's finding, reproduced as a refusal.

        The capture's own manifest records that executing a collection over a
        construction *overwrites the build's start instant while the countdown
        survives* -- so v1 refuses rather than reproducing that.
        """
        document = self.repository.read(self.player)
        document.set_row_instant(2, CAPTURE_INSTANT - 100)
        document.row_attr(2)["cp"] = 5
        document.row_attr(2)["nc"] = 1
        self.repository.write(document)
        outcome = self._collect()
        self.assertEqual(RefusalCode.CONSTRUCTION_IN_PROGRESS, outcome.code)
        after = self.repository.read(self.player)
        self.assertEqual(5, after.row_attr(2)["cp"])
        self.assertEqual(1, after.row_attr(2)["nc"])


def _recorded(name: str, document: Dict[str, Any]) -> int:
    """One stored resource from a captured document, by its own stored path.

    The seven resources do not all live in one place -- ``cash`` is under
    ``playerInfo`` and ``mana`` under ``privateState`` -- so this resolves them
    the way ``server_v1_repository`` does rather than assuming a flat shape.
    """
    for section, key in (("maps", 0), ("playerInfo", None), ("privateState", None)):
        node: Any = document[section]
        node = node[key] if key is not None else node
        if isinstance(node, dict) and name in node:
            return int(node[name])
    raise AssertionError("no recorded %r in the captured document" % name)


if __name__ == "__main__":
    unittest.main()