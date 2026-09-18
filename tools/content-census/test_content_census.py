import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

import verify_content as verifier

ROOT = Path(__file__).resolve().parents[2]

EXPECTED_KEYS = [
    "categories", "items", "inventory_items", "expansion_prices", "levels",
    "neighbor_assists", "town_prices", "map_prices", "findable_items",
    "goals", "offer_packs", "social_items", "globals", "images", "sounds",
    "collections", "level_ranking_reward", "darts_items",
    "units_collections_categories", "magics",
]

EXPECTED_PATCH_ORDER = [
    "atom_fusion_item", "unit_patch", "atom_fusion_items_data",
    "atom_fusion_powerup", "targets",
]

REFERENCE_SOURCES = ("get_game_config.py", "mods/no_hiring_needed.json")


def snapshot(root):
    return {str(path.relative_to(root)): ("directory" if path.is_dir() else
            path.read_bytes())
            for path in Path(root).rglob("*")}


def run_main(argv):
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        code = verifier.main(argv)
    return code, stderr.getvalue()


def run_stdout(argv):
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        code, _ = run_main(argv)
    return code, stdout.getvalue()


def make_work_tree():
    temporary = tempfile.TemporaryDirectory()
    work = Path(temporary.name) / "repo"
    shutil.copytree(ROOT / "config", work / "config")
    shutil.copytree(ROOT / "mods", work / "mods")
    shutil.copytree(ROOT / "docs" / "game-content", work / "docs" / "game-content")
    (work / "tools" / "content-census").mkdir(parents=True)
    shutil.copy2(ROOT / "tools" / "content-census" / "verify_content.py",
                 work / "tools" / "content-census" / "verify_content.py")
    for name in REFERENCE_SOURCES:
        shutil.copy2(ROOT / name, work / name)
    return temporary, work


class KeyExtractionTests(unittest.TestCase):
    def test_current_source_extracts_20_keys_in_canonical_order(self):
        config = verifier.load_main_config(ROOT / "config" / "main.json")
        inventory = verifier.extract_key_inventory(config)
        self.assertEqual([item["key"] for item in inventory], EXPECTED_KEYS)

    def test_current_source_shapes_and_counts(self):
        config = verifier.load_main_config(ROOT / "config" / "main.json")
        inventory = {item["key"]: item
                     for item in verifier.extract_key_inventory(config)}
        self.assertEqual(inventory["items"],
                         {"key": "items", "container_shape": "array",
                          "entry_count": 778})
        self.assertEqual(inventory["levels"],
                         {"key": "levels", "container_shape": "array",
                          "entry_count": 100})
        self.assertEqual(inventory["globals"],
                         {"key": "globals", "container_shape": "object",
                          "entry_count": 104})
        self.assertEqual(inventory["images"],
                         {"key": "images", "container_shape": "object",
                          "entry_count": 607})
        self.assertEqual(inventory["darts_items"],
                         {"key": "darts_items", "container_shape": "array",
                          "entry_count": 30})
        self.assertEqual(len(inventory), 20)

    def test_patch_list_skips_comments_and_blanks(self):
        text = ("### Add items\natom_fusion_item\n\n# comment\n"
                "unit_patch\n")
        self.assertEqual(verifier.parse_patch_list(text),
                         ["atom_fusion_item", "unit_patch"])

    def test_mods_list_reports_inactive_pipeline(self):
        text = (ROOT / "mods" / "mods.txt").read_text(encoding="utf-8")
        active, inactive = verifier.parse_mods_list(text)
        self.assertEqual(active, [])
        self.assertEqual(inactive, ["no_hiring_needed"])

    def test_top_level_list_is_unsupported(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "main.json"
            candidate.write_text("[1, 2, 3]", encoding="utf-8")
            with self.assertRaisesRegex(verifier.VerificationError,
                                        "unsupported content shape"):
                verifier.load_main_config(candidate)

    def test_non_container_key_is_unsupported(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "main.json"
            candidate.write_text('{"items": 42}', encoding="utf-8")
            with self.assertRaisesRegex(verifier.VerificationError,
                                        "unsupported content shape"):
                verifier.load_main_config(candidate)

    def test_unknown_patch_operation_is_unsupported(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "weird.json"
            candidate.write_text('[{"op": "bogus", "path": "/items/-"}]',
                                 encoding="utf-8")
            with self.assertRaisesRegex(verifier.VerificationError,
                                        "unsupported patch"):
                verifier.load_patch_file(candidate, "weird")

    def test_non_list_patch_is_unsupported(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "weird.json"
            candidate.write_text('{"op": "add"}', encoding="utf-8")
            with self.assertRaisesRegex(verifier.VerificationError,
                                        "unsupported patch shape"):
                verifier.load_patch_file(candidate, "weird")


class VerificationExitCodeTests(unittest.TestCase):
    def setUp(self):
        self.temporary, self.work = make_work_tree()
        self.addCleanup(self.temporary.cleanup)

    def load_census(self):
        return json.loads(
            (self.work / "docs" / "game-content" / "census.json").read_text(
                encoding="utf-8"))

    def save_census(self, document):
        (self.work / "docs" / "game-content" / "census.json").write_text(
            json.dumps(document, indent=2) + "\n", encoding="utf-8")

    def test_agreement_exit_0(self):
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 0)

    def test_entry_count_drift_exit_1(self):
        document = self.load_census()
        for entry in document["content_keys"]:
            if entry["name"] == "levels":
                entry["entry_count"] = 101
        self.save_census(document)
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 1)

    def test_missing_key_exit_1(self):
        document = self.load_census()
        document["content_keys"] = [entry for entry in document["content_keys"]
                                    if entry["name"] != "magics"]
        document["policy"]["key_count"] = len(document["content_keys"])
        inventory = self.work / "docs" / "game-content" / "census.md"
        text = inventory.read_text(encoding="utf-8")
        inventory.write_text(text.replace("`magics`", "`gone_key`"),
                             encoding="utf-8")
        self.save_census(document)
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 1)

    def test_patch_order_drift_exit_1(self):
        document = self.load_census()
        order = document["patches"]["order"]
        document["patches"]["order"] = [order[1], order[0]] + order[2:]
        self.save_census(document)
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 1)

    def test_patch_op_count_drift_exit_1(self):
        document = self.load_census()
        for entry in document["patches"]["entries"]:
            if entry["name"] == "unit_patch":
                entry["op_count"] = 122
                entry["op_counts"] = {"add": 122}
        self.save_census(document)
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 1)

    def test_mods_status_change_exit_1(self):
        mods = self.work / "mods" / "mods.txt"
        text = mods.read_text(encoding="utf-8")
        mods.write_text(text.rstrip("\n") + "\nno_hiring_needed\n",
                        encoding="utf-8")
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 1)

    def test_inventory_drift_exit_1(self):
        inventory = self.work / "docs" / "game-content" / "census.md"
        text = inventory.read_text(encoding="utf-8")
        inventory.write_text(text.replace("`magics`", "`gone_key`"),
                             encoding="utf-8")
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 1)

    def test_unsupported_shape_exit_2(self):
        # Trailing newlines keep every census source reference in range so
        # the failure deterministically surfaces as an unsupported shape.
        (self.work / "config" / "main.json").write_text(
            '{\n"items": 42\n}' + "\n" * 51260, encoding="utf-8")
        code, stderr = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 2)
        self.assertIn("unsupported content shape", stderr)

    def test_unsupported_patch_operation_exit_2(self):
        target = self.work / "config" / "patch" / "targets.json"
        # Trailing newlines keep the census source reference in range so
        # the failure deterministically surfaces as an unsupported patch.
        target.write_text('[{"op": "bogus", "path": "/darts_items"}]'
                          + "\n" * 400,
                          encoding="utf-8")
        code, stderr = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 2)
        self.assertIn("unsupported patch", stderr)

    def test_source_reference_out_of_range_exit_2(self):
        document = self.load_census()
        total = len((self.work / "get_game_config.py").read_text(
            encoding="utf-8").splitlines())
        patched = False
        for entry in document["content_keys"]:
            for reference in entry["source_references"]:
                if reference["file"] == "config/main.json":
                    reference["end_line"] = 10 ** 9
                    patched = True
                    break
            if patched:
                break
        self.assertTrue(patched)
        self.save_census(document)
        code, stderr = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 2)
        self.assertIn("out of range", stderr)
        self.assertGreater(total, 0)

    def test_invalid_census_exit_2(self):
        (self.work / "docs" / "game-content" / "census.json").write_text(
            "{broken", encoding="utf-8")
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 2)

    def test_unparseable_content_exit_2(self):
        (self.work / "config" / "main.json").write_text("{broken",
                                                       encoding="utf-8")
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 2)

    def test_missing_files_exit_2(self):
        (self.work / "docs" / "game-content" / "census.md").unlink()
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 2)


class ConsistencyAndContainmentTests(unittest.TestCase):
    def test_census_entries_match_source_keys(self):
        config = verifier.load_main_config(ROOT / "config" / "main.json")
        census = json.loads((ROOT / "docs" / "game-content" / "census.json").read_text(
            encoding="utf-8"))
        inventory = {item["key"]: item
                     for item in verifier.extract_key_inventory(config)}
        self.assertEqual(len(census["content_keys"]), 20)
        self.assertEqual(census["policy"]["key_count"], 20)
        self.assertEqual(census["policy"]["patch_count"], 5)
        for entry in census["content_keys"]:
            source = inventory[entry["name"]]
            self.assertEqual(entry["container_shape"], source["container_shape"])
            self.assertEqual(entry["entry_count"], source["entry_count"])
        self.assertEqual(census["patches"]["order"], EXPECTED_PATCH_ORDER)
        self.assertEqual(census["mods"]["active_mods"], [])
        self.assertEqual(census["mods"]["inactive_mods"], ["no_hiring_needed"])

    def test_inventory_covers_every_census_entry(self):
        census = json.loads((ROOT / "docs" / "game-content" / "census.json").read_text(
            encoding="utf-8"))
        inventory = (ROOT / "docs" / "game-content" / "census.md").read_text(
            encoding="utf-8")
        for entry in census["content_keys"]:
            self.assertIn(entry["name"], inventory)
        for name in census["patches"]["order"]:
            self.assertIn(name, inventory)
        lowered = inventory.lower()
        self.assertIn("inactive", lowered)
        self.assertIn("mods", lowered)
        self.assertIn("stored", lowered)
        self.assertIn("served", lowered)
        self.assertIn("make_dynamic", inventory)
        self.assertIn("remove_duplicate_items", inventory)

    def test_repeated_runs_are_byte_identical(self):
        code_one, out_one = run_stdout(["--repo-root", str(ROOT)])
        code_two, out_two = run_stdout(["--repo-root", str(ROOT)])
        self.assertEqual(code_one, 0)
        self.assertEqual(code_two, 0)
        self.assertEqual(out_one, out_two)

    def test_verifier_reads_only_expected_files_and_writes_nothing(self):
        temporary, work = make_work_tree()
        try:
            census = json.loads((work / "docs" / "game-content" / "census.json").read_text(
                encoding="utf-8"))
            expected = {
                str(Path("config") / "main.json").replace("\\", "/"),
                str(Path("config") / "patch" / "patches.txt").replace("\\", "/"),
                str(Path("docs") / "game-content" / "census.json").replace("\\", "/"),
                str(Path("docs") / "game-content" / "census.md").replace("\\", "/"),
                str(Path("mods") / "mods.txt").replace("\\", "/"),
            }
            for name in census["patches"]["order"]:
                expected.add(str(Path("config") / "patch" / (name + ".json")).replace(
                    "\\", "/"))
            for entry in census["content_keys"]:
                for reference in entry.get("source_references", []):
                    expected.add(reference["file"])
            for entry in census["patches"]["entries"]:
                for reference in entry.get("source_references", []):
                    expected.add(reference["file"])
            for reference in census["mods"].get("source_references", []):
                expected.add(reference["file"])
            for reference in census["duplicate_cleaning"].get("source_references", []):
                expected.add(reference["file"])
            for reference in census["dynamic_derivation"].get("source_references", []):
                expected.add(reference["file"])
            opened = []
            real_io_open = io.open

            def guarded_open(file, mode="r", *args, **kwargs):
                if any(flag in str(mode) for flag in ("w", "a", "x", "+")):
                    raise AssertionError("unexpected write open: %r" % (file,))
                opened.append(str(file))
                return real_io_open(file, mode, *args, **kwargs)

            before = snapshot(work)
            # pathlib.Path.read_bytes resolves to io.open, not builtins.open,
            # so both entry points are guarded.
            with mock.patch("io.open", guarded_open), \
                    mock.patch("builtins.open", guarded_open):
                code, _ = run_main(["--repo-root", str(work)])
            self.assertEqual(code, 0)
            self.assertEqual(snapshot(work), before)
            observed = set()
            for raw in opened:
                try:
                    observed.add(str(Path(raw).relative_to(work)).replace("\\", "/"))
                except ValueError:
                    self.fail("verifier read outside repo root: %r" % (raw,))
            self.assertEqual(observed, expected)
        finally:
            temporary.cleanup()

    def test_no_legacy_module_imports(self):
        source = (ROOT / "tools" / "content-census" / "verify_content.py").read_text(
            encoding="utf-8")
        for forbidden in ("import flask", "from flask", "jsonpatch",
                          "import get_game_config", "from get_game_config",
                          "import server", "from server", "import command",
                          "from command", "import engine", "from engine",
                          "import requests", "subprocess", "socket",
                          "urllib", "webbrowser", "http.server"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
