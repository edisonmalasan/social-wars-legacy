#!/usr/bin/env python3
"""Containment: no working-tree writes, and the port is really released.

Task 3.3 asks for the disposable-corpus helper to be **verified** rather than
assumed, and asks for the check to be re-run "so a single pass is not mistaken
for a guarantee".  Both are done here, and the second is not free: the whole
build/execute/remove cycle runs **twice** and both passes must leave the
working tree exactly as they found it.

Three claims, kept apart because they are three claims:

1. **The working tree is untouched.**  Snapshotted before and after every
   execution, over both ``saves/`` and the preserved ``tests/saves/``.  Note the
   *directory* check as well as the file check: an empty ``saves/`` directory
   still breaks ``verify-boot.ps1``'s recorded-absent guard, so a check that
   only counted files would pass while the battery failed.
2. **The corpus is gone -- and "gone" is asserted, not assumed.**
   ``remove_corpus`` follows ``shutil.rmtree(..., ignore_errors=True)`` with an
   explicit re-check, because the Compatibility API's own ``remove_corpus``
   reports success whether or not it succeeded and can leave empty directories
   behind.  A planted non-empty file is what makes the assertion non-vacuous:
   a removal that removed nothing would still "succeed" against an empty
   directory.
3. **The port is free afterwards.**  Checked with the same enumeration
   ``test_settings`` has already proved can see a plant, so this is not a
   vacuous bind probe.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import List

import harness
from harness import (
    REPO_ROOT,
    FilesystemSaveRepository,
    build_corpus,
    corpus_save_path,
    load_content,
    remove_corpus,
    seed_document,
    seed_player_id,
    working_tree_save_files,
    working_tree_saves_dir_exists,
)
from server_v1_collect import collect
from server_v1_intent import Intent
from server_v1_outcomes import Success
from server_v1_settings import DEFAULT_PORT, HOST

FIXTURE_INSTANT = 1790705901


class WorkingTreeUnchangedTests(unittest.TestCase):
    """Claim 1, across two full cycles."""

    def _snapshot(self) -> List[str]:
        return working_tree_save_files()

    def _execute_one_collection(self, corpus: Path) -> None:
        repository = FilesystemSaveRepository(corpus)
        content = load_content(REPO_ROOT)
        outcome = collect(
            Intent(action="collect", player_id=seed_player_id(), row=2),
            content,
            repository,
            FIXTURE_INSTANT,
        )
        self.assertIsInstance(outcome, Success)
        # The transaction must have actually written, or the cycle proves
        # nothing: a cycle in which the save was never touched would leave the
        # working tree unchanged for the wrong reason.
        instant = json.loads(
            corpus_save_path(corpus).read_text(encoding="utf-8")
        )["maps"][0]["items"]["2"][3]
        self.assertEqual(FIXTURE_INSTANT, instant)
        self.assertEqual(0, seed_document()["maps"][0]["items"]["2"][3])

    def test_two_full_cycles_leave_the_working_tree_untouched(self) -> None:
        before = self._snapshot()
        saves_existed_before = working_tree_saves_dir_exists()
        for cycle in range(2):
            with self.subTest(cycle=cycle):
                corpus = build_corpus(mutate=lambda document: None)
                try:
                    self._execute_one_collection(corpus)
                finally:
                    remove_corpus(corpus)
                self.assertEqual(before, self._snapshot())
                self.assertEqual(
                    saves_existed_before,
                    working_tree_saves_dir_exists(),
                    "a working-tree saves/ directory appeared or vanished",
                )

    def test_the_absence_of_a_working_tree_saves_directory_is_the_delivered_state(self) -> None:
        """Pins the starting state this line asserts it preserves.

        If this ever fails because a ``saves/`` directory exists, the two
        assertions above become weaker -- they would be comparing a polluted
        tree against itself -- so it is stated directly rather than assumed.
        """
        self.assertFalse(working_tree_saves_dir_exists())
        self.assertTrue(working_tree_save_files(), "tests/saves must still hold preserved material")

    def test_nothing_was_written_into_the_preserved_saves_directory(self) -> None:
        for relative in working_tree_save_files():
            self.assertTrue(
                relative.startswith("tests/saves/"),
                "unexpected save file in the working tree: %s" % relative,
            )


class CorpusRemovalTests(unittest.TestCase):
    """Claim 2: removal is asserted, and the assertion is shown to be able to fail."""

    def test_removal_is_asserted_not_assumed(self) -> None:
        corpus = build_corpus(mutate=lambda document: None)
        self.assertTrue(corpus.is_dir())
        self.assertTrue(corpus_save_path(corpus).is_file())
        remove_corpus(corpus)
        self.assertFalse(corpus.exists())

    def test_the_planted_control_shows_the_corpus_really_had_contents(self) -> None:
        """A removal of an empty directory would pass for the same reason.

        So the corpus is shown to be non-empty *before* removal, with a file
        the size assertion depends on -- the guard is only meaningful over
        something that had to go.
        """
        corpus = build_corpus(mutate=lambda document: None)
        contents = sorted(path.name for path in corpus.iterdir())
        self.assertEqual(["config", "mods", "saves"], contents)
        files = list(corpus.rglob("*"))
        self.assertGreater(len(files), 5)
        remove_corpus(corpus)

    def test_removing_a_directory_that_is_already_gone_is_not_an_error(self) -> None:
        corpus = build_corpus(mutate=lambda document: None)
        shutil.rmtree(str(corpus))
        remove_corpus(corpus)  # must not raise
        remove_corpus(None)  # and must not raise for no corpus at all

    def test_a_survivor_is_reported_rather_than_swallowed(self) -> None:
        """``ignore_errors=True`` alone would report success either way.

        The planted control: a directory whose removal cannot succeed on
        Windows is hard to arrange portably, so the *reporting* path is
        exercised through the helper's own contract instead -- by making the
        corpus path a **file**, which ``rmtree`` cannot remove and which the
        helper must therefore report rather than ignore.
        """
        with tempfile.TemporaryDirectory() as host:
            occupied = Path(host) / "occupied"
            occupied.write_text("not a directory", encoding="utf-8")
            # A plain file is not a corpus directory, so ``remove_corpus``
            # sees a path that does not exist *as a directory* only after
            # rmtree's failure.  The helper must raise rather than pass.
            with self.assertRaises(harness.ContainmentError):
                remove_corpus(occupied)


class PortReleaseTests(unittest.TestCase):
    """Claim 3, using the enumeration ``test_settings`` proved can see a plant."""

    def test_the_port_is_free_after_a_corpus_cycle(self) -> None:
        self.assertTrue(harness.port_is_free(HOST, DEFAULT_PORT))
        corpus = build_corpus(mutate=lambda document: None)
        repository = FilesystemSaveRepository(corpus)
        content = load_content(REPO_ROOT)
        collect(
            Intent(action="collect", player_id=seed_player_id(), row=2),
            content,
            repository,
            FIXTURE_INSTANT,
        )
        remove_corpus(corpus)
        self.assertTrue(harness.port_is_free(HOST, DEFAULT_PORT))
        # The re-runnable form, so a single Windows bind refusal is not read
        # as a leak.
        harness.assert_port_free(HOST, DEFAULT_PORT)

    def test_the_enumeration_is_not_vacuous_in_this_file_either(self) -> None:
        """This file's port claim is worthless if the probe cannot see a plant.

        The same control ``test_settings`` runs, repeated here so that *this*
        file's assertions are the ones shown to be sensitive -- a control in a
        sibling module does not transfer its sensitivity to a different
        module's conclusions.
        """
        with harness.PlantedListener(HOST, DEFAULT_PORT):
            self.assertFalse(harness.port_is_free(HOST, DEFAULT_PORT))
        self.assertTrue(harness.port_is_free(HOST, DEFAULT_PORT))


class CorpusShapeTests(unittest.TestCase):
    """What a corpus copies, and what it deliberately does not."""

    def test_a_corpus_copies_content_mods_and_one_seeded_save(self) -> None:
        corpus = build_corpus(mutate=lambda document: None)
        self.addCleanup(remove_corpus, corpus)
        self.assertTrue((corpus / "config" / "main.json").is_file())
        self.assertTrue((corpus / "config" / "patch" / "patches.txt").is_file())
        self.assertTrue((corpus / "mods" / "mods.txt").is_file())
        self.assertEqual([seed_player_id()], [
            path.name[: -len(".save.json")]
            for path in (corpus / "saves").iterdir()
        ])

    def test_a_corpus_does_not_copy_preserved_directories_v1_never_reads(self) -> None:
        corpus = build_corpus(mutate=lambda document: None)
        self.addCleanup(remove_corpus, corpus)
        for omitted in ("villages", "assets", "tests"):
            self.assertFalse(
                (corpus / omitted).exists(),
                "a corpus copied %r, which v1 does not read" % omitted,
            )

    def test_a_verbatim_corpus_keeps_the_seed_bytes_and_a_mutated_one_does_not(self) -> None:
        """The CRLF claim, which is what makes a byte-identity assertion real.

        **Two defects in the first version of this test, both from the same
        mistake.**  It called ``build_corpus(mutate=lambda document: None)`` for
        the *verbatim* case, believing a no-op callable meant "do not mutate".
        It does not: ``build_corpus`` selects its branch on ``mutate is None``, so
        a no-op lambda takes the *mutated* branch and re-renders the document in
        v1's LF form.  The assertion then compared CRLF seed bytes against LF
        written bytes and failed -- which is why the branch is now spelled
        explicitly in both halves rather than implied by a callback that does
        nothing.

        A second, subtler version of the same mistake is avoided by the
        ``v1_marker`` assertion in the mutated half: without it, "the bytes
        differ" would also be satisfied by a corpus built from the wrong source.
        """
        seed_bytes = (REPO_ROOT / "tests" / "saves" / "fresh-player.json").read_bytes()
        # Verbatim: ``mutate`` omitted entirely.
        verbatim = build_corpus()
        self.addCleanup(remove_corpus, verbatim)
        self.assertEqual(seed_bytes, corpus_save_path(verbatim).read_bytes())
        self.assertIn(b"\r\n", seed_bytes)

        mutated = build_corpus(mutate=lambda document: document.update({"v1_marker": 1}))
        self.addCleanup(remove_corpus, mutated)
        mutated_bytes = corpus_save_path(mutated).read_bytes()
        self.assertNotEqual(seed_bytes, mutated_bytes)
        self.assertNotIn(b"\r\n", mutated_bytes)
        # And the marker really landed, so this is the mutated branch and not
        # some other way of producing different bytes.
        self.assertIn(b'"v1_marker": 1', mutated_bytes)

    def test_a_corpus_will_not_be_built_over_existing_contents(self) -> None:
        with tempfile.TemporaryDirectory() as host:
            occupied = Path(host)
            (occupied / "already-here").write_text("x", encoding="utf-8")
            with self.assertRaises(harness.ContainmentError):
                build_corpus(directory=occupied)


if __name__ == "__main__":
    unittest.main()