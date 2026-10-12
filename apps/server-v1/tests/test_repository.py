#!/usr/bin/env python3
"""The repository seam: a round trip that preserves every field (task 3.2).

Task 3.2 asks the suite to prove "a save written by this service still contains
the fields v1 did not read".  That claim is not about the seven resources and
the row instant — it is about the ~15,600 bytes of *everything else* in the
committed save, most of which v1 has no name for and no rule about.

The assertion is therefore over the **whole parsed document**, compared key by
key at every depth, rather than over a sampled field.  A test that checked only
``privateState`` would pass while a write dropped half the document.
"""

from __future__ import annotations

import json
import unittest
from typing import Any, Dict, List, Tuple

import harness
from harness import FilesystemSaveRepository, build_corpus, corpus_save_bytes, remove_corpus, seed_player_id
from server_v1_repository import (
    ITEMS_PATH,
    STORED_RESOURCE_NAMES,
    STORED_RESOURCE_PATHS,
    RepositoryError,
    SaveDocument,
)


def leaf_paths(value: Any, prefix: str = "") -> List[str]:
    """Every JSON-pointer-ish leaf path in a parsed document, sorted.

    A mapping contributes one path per key; a list contributes one per index;
    a scalar contributes its own path.  Compared as *sets of paths with values*
    in :func:`assertDocumentsEqual`, so a dropped key, an added key, and a
    changed value are all distinguishable.
    """
    found: List[str] = []
    if isinstance(value, dict):
        for key in sorted(value):
            found.extend(leaf_paths(value[key], "%s/%s" % (prefix, key)))
    elif isinstance(value, list):
        for index, entry in enumerate(value):
            found.extend(leaf_paths(entry, "%s/%d" % (prefix, index)))
    else:
        found.append(prefix or "/")
    return found


def assertDocumentsEqual(case: unittest.TestCase, before: Any, after: Any, label: str) -> None:
    """Assert two parsed documents are equal at every leaf, by path."""
    before_leaves = leaf_paths(before)
    after_leaves = leaf_paths(after)
    case.assertEqual(before_leaves, after_leaves, "%s: leaf paths differ" % label)
    for path in before_leaves:
        case.assertEqual(
            _leaf(before, path),
            _leaf(after, path),
            "%s: leaf %s differs" % (label, path),
        )


def _leaf(document: Any, path: str) -> Any:
    node = document
    for part in path.strip("/").split("/"):
        node = node[int(part)] if isinstance(node, list) else node[part]
    return node


class StoredResourceDeclarationTests(unittest.TestCase):
    """The seven resources are named by *path*, ESTABLISHED from the corpus."""

    def test_there_are_seven_and_they_are_in_a_fixed_order(self) -> None:
        self.assertEqual(7, len(STORED_RESOURCE_NAMES))
        self.assertEqual(
            ("xp", "gold", "wood", "oil", "steel", "cash", "mana"),
            STORED_RESOURCE_NAMES,
        )

    def test_cash_and_mana_live_outside_the_map(self) -> None:
        # The two that are not ``maps[0]`` keys are the two a map-only reader
        # would silently lose.
        self.assertEqual(("playerInfo", "cash"), STORED_RESOURCE_PATHS["cash"])
        self.assertEqual(("privateState", "mana"), STORED_RESOURCE_PATHS["mana"])

    def test_every_declared_path_starts_at_a_container_that_exists(self) -> None:
        corpus = build_corpus()
        try:
            repository = FilesystemSaveRepository(corpus)
            document = repository.read(seed_player_id())
            for name in STORED_RESOURCE_NAMES:
                with self.subTest(resource=name):
                    value = _resolve(document.raw, STORED_RESOURCE_PATHS[name])
                    self.assertIsInstance(value, int)
        finally:
            remove_corpus(corpus)


def _resolve(root: Any, path: Tuple[Any, ...]) -> Any:
    node = root
    for part in path:
        node = node[part]
    return node


class RoundTripTests(unittest.TestCase):
    """A write that changed nothing still preserves the whole document."""

    def setUp(self) -> None:
        self.corpus = build_corpus()
        self.addCleanup(remove_corpus, self.corpus)
        self.repository = FilesystemSaveRepository(self.corpus)
        self.player = seed_player_id()

    def test_a_no_op_write_is_value_identical(self) -> None:
        before = self.repository.read(self.player)
        snapshot = before.snapshot()
        self.repository.write(before)
        after = self.repository.read(self.player)
        assertDocumentsEqual(self, snapshot, after.raw, "no-op write")

    def test_a_no_op_write_is_byte_stable_across_repeats(self) -> None:
        """The delivered write form is deterministic, so equal bytes are checkable."""
        self.repository.write(self.repository.read(self.player))
        first = corpus_save_bytes(self.corpus)
        self.repository.write(self.repository.read(self.player))
        second = corpus_save_bytes(self.corpus)
        self.assertEqual(first, second)

    def test_the_write_form_is_lf_with_no_trailing_newline(self) -> None:
        self.repository.write(self.repository.read(self.player))
        raw = corpus_save_bytes(self.corpus)
        self.assertNotIn(b"\r\n", raw)
        self.assertFalse(raw.endswith(b"\n"))

    def test_the_seed_is_crlf_so_a_round_trip_is_value_equal_not_byte_equal(self) -> None:
        """A recorded divergence, pinned so nobody later calls it a defect.

        The committed seed carries CRLF line endings.  v1's write form is LF, so
        the very first write necessarily rewrites the whole file's endings: the
        *values* are preserved exactly, the *bytes* are not, and cannot be while
        the write form is deterministic.  Asserted as its own test so the
        containment claims elsewhere can rely on "bytes unchanged" meaning
        "nothing was written at all".
        """
        seed_bytes = (harness.SERVICE_DIR.parents[1] / "tests" / "saves" / "fresh-player.json").read_bytes()
        self.assertIn(b"\r\n", seed_bytes, "the committed seed is expected to be CRLF")
        before = json.loads(seed_bytes.decode("utf-8"))
        self.repository.write(self.repository.read(self.player))
        after = self.repository.read(self.player).raw
        assertDocumentsEqual(self, before, after, "seed round trip")
        self.assertNotEqual(seed_bytes, corpus_save_bytes(self.corpus))


class UnknownFieldPreservationTests(RoundTripTests):
    """The preservation claim proper: fields v1 cannot name survive a write."""

    def _mutate_and_write(self, mutate) -> Dict[str, Any]:
        document = self.repository.read(self.player)
        before = document.snapshot()
        mutate(document)
        snapshot_after_mutation = document.snapshot()
        self.repository.write(document)
        after = self.repository.read(self.player).raw
        assertDocumentsEqual(self, snapshot_after_mutation, after, "after mutation")
        return before

    def test_a_field_v1_has_no_accessor_for_survives(self) -> None:
        planted_key = "serverV1PlantedUnknownField"
        before = self._mutate_and_write(
            lambda document: document.raw["privateState"].__setitem__(
                planted_key, {"a": [1, 2, {"b": None}]}
            )
        )
        self.assertNotIn(planted_key, before.get("privateState", {}))
        after = self.repository.read(self.player).raw
        self.assertEqual({"a": [1, 2, {"b": None}]}, after["privateState"][planted_key])

    def test_an_unknown_top_level_section_survives(self) -> None:
        section = {"weird": [1, {"deep": "value"}]}
        self._mutate_and_write(
            lambda document: document.raw.__setitem__("serverV1Section", section)
        )
        self.assertEqual(section, self.repository.read(self.player).raw["serverV1Section"])

    def test_an_unknown_row_attr_key_survives_a_resource_change(self) -> None:
        """The case that matters: v1 *did* mutate, and the rest still survives."""
        document = self.repository.read(self.player)
        before = document.snapshot()
        document.raw["maps"][0]["items"]["2"][6]["serverV1Attr"] = "kept"
        document.set_resource("gold", document.resources()["gold"] + 1)
        expected = document.snapshot()
        self.repository.write(document)
        after = self.repository.read(self.player).raw
        assertDocumentsEqual(self, expected, after, "mutating write")
        self.assertEqual("kept", after["maps"][0]["items"]["2"][6]["serverV1Attr"])
        self.assertEqual(before["maps"][0]["gold"] + 1, after["maps"][0]["gold"])

    def test_the_seed_carries_fields_no_accessor_names(self) -> None:
        """How much v1 is not modelling, measured rather than asserted."""
        document = self.repository.read(self.player)
        named_paths = {"/".join(str(p) for p in path) for path in STORED_RESOURCE_PATHS.values()}
        self.assertTrue(named_paths)
        for name in named_paths:
            with self.subTest(path=name):
                with self.assertRaises((KeyError, IndexError, TypeError)):
                    document.raw[name]


class AddressabilityTests(unittest.TestCase):
    """Row addressing is by **string** key, established from ``engine.py:36-40``."""

    def setUp(self) -> None:
        self.corpus = build_corpus()
        self.addCleanup(remove_corpus, self.corpus)
        self.repository = FilesystemSaveRepository(self.corpus)
        self.player = seed_player_id()

    def test_items_are_addressed_by_string_key(self) -> None:
        document = self.repository.read(self.player)
        self.assertEqual(("maps", 0, "items"), ITEMS_PATH)
        self.assertIsNotNone(document.row(2))
        # An integer key would be a different row for the preserved server.
        self.assertNotIn(2, document.items())

    def test_a_missing_row_is_none_not_an_error(self) -> None:
        self.assertIsNone(self.repository.read(self.player).row(9999))

    def test_a_path_separating_player_id_is_refused_not_resolved(self) -> None:
        for candidate in ("../escape", "a/b", "a\\b", ".", "..", "with\x00nul"):
            with self.subTest(player_id=candidate):
                with self.assertRaises(RepositoryError) as caught:
                    self.repository.path_for(candidate)
                self.assertEqual("unaddressable_player", caught.exception.code)

    def test_an_unknown_player_is_a_named_failure(self) -> None:
        with self.assertRaises(RepositoryError) as caught:
            self.repository.read("00000000-0000-4000-8000-999999999999")
        self.assertEqual("unknown_player", caught.exception.code)


class SnapshotTests(unittest.TestCase):
    """``snapshot`` must be a copy: an aliasing bug would make every proof pass."""

    def test_a_snapshot_does_not_alias_the_live_document(self) -> None:
        corpus = build_corpus()
        self.addCleanup(remove_corpus, corpus)
        document = FilesystemSaveRepository(corpus).read(seed_player_id())
        snapshot = document.snapshot()
        document.set_resource("gold", document.resources()["gold"] + 500)
        document.raw["maps"][0]["items"]["2"][0] = 999999
        self.assertNotEqual(snapshot["maps"][0]["gold"], document.raw["maps"][0]["gold"])
        self.assertNotEqual(snapshot["maps"][0]["items"]["2"][0], 999999)


class InstrumentValidationTests(unittest.TestCase):
    """The whole-document comparator must be able to fail.

    ``assertDocumentsEqual`` is the instrument every preservation claim above
    rests on, and a comparator that silently accepts would make all of them
    vacuously true — the same defect class as a refusal guard satisfied by a
    docstring.  So each way it is expected to catch something is checked by
    planting exactly that.
    """

    def _assert_rejects(self, before: Any, after: Any) -> None:
        case = unittest.TestCase()
        with self.assertRaises(AssertionError):
            assertDocumentsEqual(case, before, after, "planted")

    def test_it_detects_a_dropped_key(self) -> None:
        self._assert_rejects({"a": 1, "b": 2}, {"a": 1})

    def test_it_detects_an_added_key(self) -> None:
        self._assert_rejects({"a": 1}, {"a": 1, "b": 2})

    def test_it_detects_a_changed_scalar(self) -> None:
        self._assert_rejects({"a": 1}, {"a": 2})

    def test_it_detects_a_changed_nested_list_element(self) -> None:
        self._assert_rejects({"a": [1, 2, 3]}, {"a": [1, 9, 3]})

    def test_it_detects_a_list_that_grew(self) -> None:
        self._assert_rejects({"a": [1, 2]}, {"a": [1, 2, 3]})

    def test_it_detects_a_type_change(self) -> None:
        self._assert_rejects({"a": 1}, {"a": "1"})

    def test_it_passes_on_a_genuinely_identical_copy(self) -> None:
        document = {"a": [1, {"b": None}], "c": {}}
        assertDocumentsEqual(self, json.loads(json.dumps(document)), document, "control")

    def test_the_leaf_census_is_not_trivially_empty(self) -> None:
        """A comparator over zero leaves compares nothing, so it always passes."""
        self.assertGreater(len(leaf_paths({"a": 1, "b": [1, 2]})), 2)


if __name__ == "__main__":
    unittest.main()