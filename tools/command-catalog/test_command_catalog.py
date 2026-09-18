import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

import verify_commands as verifier

ROOT = Path(__file__).resolve().parents[2]


def snapshot(root):
    return {str(path.relative_to(root)): ("directory" if path.is_dir() else
            path.read_bytes())
            for path in Path(root).rglob("*")}


def run_main(argv, cwd=None):
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        code = verifier.main(argv)
    return code, stderr.getvalue()


def run_stdout(argv):
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        code, _ = run_main(argv)
    return code, stdout.getvalue()


class BranchExtractionTests(unittest.TestCase):
    def test_current_source_extracts_63_named_branches(self):
        source = (ROOT / "command.py").read_text(encoding="utf-8")
        branches = verifier.extract_command_branches(source)
        names = [b["command"] for b in branches]
        self.assertEqual(len(names), 63)
        self.assertEqual(len(set(names)), 63)
        for expected in ("buy", "level_up", "ping", "set_variables",
                         "fast_forward", "flash_debug", "end_attack",
                         "admin_set_quest_rank"):
            self.assertIn(expected, names)
        self.assertNotIn("push_dead_unit", names)

    def test_fallthrough_is_not_a_branch(self):
        source = (ROOT / "command.py").read_text(encoding="utf-8")
        branches = verifier.extract_command_branches(source)
        names = [b["command"] for b in branches]
        self.assertNotIn("(unhandled)", names)
        self.assertNotIn("else", names)

    def test_non_literal_comparison_is_unsupported(self):
        source = ("def do_command(USERID, map_id, cmd, args, resources_changed):\n"
                  "    if cmd == SOME_CONST:\n"
                  "        return\n")
        with self.assertRaisesRegex(verifier.VerificationError, "unsupported dispatch syntax"):
            verifier.extract_command_branches(source)

    def test_membership_test_is_unsupported(self):
        source = ("def do_command(USERID, map_id, cmd, args, resources_changed):\n"
                  "    if cmd in ('ping', 'pong'):\n"
                  "        return\n")
        with self.assertRaisesRegex(verifier.VerificationError, "unsupported dispatch syntax"):
            verifier.extract_command_branches(source)

    def test_wrong_variable_is_ignored(self):
        source = ("def do_command(USERID, map_id, cmd, args, resources_changed):\n"
                  "    if args == 'ping':\n"
                  "        return\n"
                  "    if cmd == 'ping':\n"
                  "        return\n")
        branches = verifier.extract_command_branches(source)
        self.assertEqual([b["command"] for b in branches], ["ping"])

    def test_missing_dispatcher_is_unsupported(self):
        with self.assertRaisesRegex(verifier.VerificationError, "unsupported dispatch syntax"):
            verifier.extract_command_branches("def other():\n    pass\n")

    def test_duplicate_branch_is_unsupported(self):
        source = ("def do_command(USERID, map_id, cmd, args, resources_changed):\n"
                  "    if cmd == 'ping':\n"
                  "        return\n"
                  "    elif cmd == 'ping':\n"
                  "        return\n")
        with self.assertRaisesRegex(verifier.VerificationError, "unsupported dispatch syntax"):
            verifier.extract_command_branches(source)


class VerificationExitCodeTests(unittest.TestCase):
    REFERENCED_SOURCES = ("engine.py", "sessions.py", "get_game_config.py",
                          "command.py")

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name) / "repo"
        shutil.copytree(ROOT / "docs" / "legacy-protocol", self.work / "docs" / "legacy-protocol")
        (self.work / "tools").mkdir()
        shutil.copy2(ROOT / "command.py", self.work / "command.py")
        for name in self.REFERENCED_SOURCES:
            source = ROOT / name
            if source.is_file() and name != "command.py":
                shutil.copy2(source, self.work / name)
        shutil.copy2(ROOT / "tools" / "command-catalog" / "verify_commands.py",
                     self.work / "tools" / "verify_commands.py")

    def load_catalog(self):
        return json.loads((self.work / "docs" / "legacy-protocol" / "commands.json").read_text(encoding="utf-8"))

    def save_catalog(self, document):
        (self.work / "docs" / "legacy-protocol" / "commands.json").write_text(
            json.dumps(document, indent=2) + "\n", encoding="utf-8")

    def test_agreement_exit_0(self):
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 0)

    def test_missing_branch_exit_1(self):
        document = self.load_catalog()
        document["commands"] = [e for e in document["commands"] if e["name"] != "ping"]
        document["policy"]["entry_count"] = len(document["commands"])
        document["policy"]["branch_count"] = len(
            [e for e in document["commands"] if e["classification"] == "handled"])
        inventory = self.work / "docs" / "legacy-protocol" / "commands.md"
        text = inventory.read_text(encoding="utf-8")
        inventory.write_text(text.replace("`ping`", "`pong-reserved`"), encoding="utf-8")
        self.save_catalog(document)
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 1)

    def test_extra_branch_exit_1(self):
        document = self.load_catalog()
        phantom = dict(document["commands"][0])
        phantom["name"] = "phantom_command"
        document["commands"].append(phantom)
        document["policy"]["entry_count"] = len(document["commands"])
        document["policy"]["branch_count"] = len(
            [e for e in document["commands"] if e["classification"] == "handled"])
        self.save_catalog(document)
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 1)

    def test_inventory_drift_exit_1(self):
        inventory = self.work / "docs" / "legacy-protocol" / "commands.md"
        text = inventory.read_text(encoding="utf-8")
        inventory.write_text(text.replace("`fast_forward`", "`gone_command`"), encoding="utf-8")
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 1)

    def test_unsupported_syntax_exit_2(self):
        source = self.work / "command.py"
        text = source.read_text(encoding="utf-8")
        text = text.replace('if cmd == "buy":', "if cmd == UNKNOWN_NAME:")
        source.write_text(text, encoding="utf-8")
        code, stderr = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 2)
        self.assertIn("unsupported dispatch syntax", stderr)

    def test_source_reference_out_of_range_exit_2(self):
        document = self.load_catalog()
        engine = (self.work / "engine.py").read_text(encoding="utf-8")
        total = len(engine.splitlines())
        patched = False
        for entry in document["commands"]:
            for reference in entry["source_references"]:
                if reference["file"] == "engine.py":
                    reference["end_line"] = total + 1
                    patched = True
                    break
            if patched:
                break
        self.assertTrue(patched)
        self.save_catalog(document)
        code, stderr = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 2)
        self.assertIn("out of range", stderr)

    def test_invalid_catalog_exit_2(self):
        (self.work / "docs" / "legacy-protocol" / "commands.json").write_text("{broken",
                                                                              encoding="utf-8")
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 2)

    def test_unparseable_source_exit_2(self):
        (self.work / "command.py").write_text("def broken(:\n", encoding="utf-8")
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 2)

    def test_missing_files_exit_2(self):
        (self.work / "docs" / "legacy-protocol" / "commands.md").unlink()
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 2)


class ConsistencyAndContainmentTests(unittest.TestCase):
    def test_catalog_entries_match_source_branches(self):
        source = (ROOT / "command.py").read_text(encoding="utf-8")
        catalog = json.loads((ROOT / "docs" / "legacy-protocol" / "commands.json").read_text(encoding="utf-8"))
        branches = verifier.extract_command_branches(source)
        handled = [e for e in catalog["commands"] if e["classification"] == "handled"]
        fallthrough = [e for e in catalog["commands"] if e["classification"] == "fallthrough"]
        self.assertEqual(len(branches), 63)
        self.assertEqual(len(handled), 63)
        self.assertEqual(len(fallthrough), 1)
        self.assertEqual({b["command"] for b in branches}, {e["name"] for e in handled})
        self.assertEqual(catalog["policy"]["branch_count"], 63)
        self.assertEqual(catalog["policy"]["entry_count"], 64)

    def test_inventory_covers_every_catalog_command(self):
        catalog = json.loads((ROOT / "docs" / "legacy-protocol" / "commands.json").read_text(encoding="utf-8"))
        inventory = (ROOT / "docs" / "legacy-protocol" / "commands.md").read_text(encoding="utf-8")
        for entry in catalog["commands"]:
            self.assertIn(entry["name"], inventory)
        lowered = inventory.lower()
        self.assertIn("time-manipulation", lowered)
        self.assertIn("never a production", lowered)
        self.assertIn("alliance", lowered)
        self.assertIn("not implemented", lowered)
        self.assertIn("apply_resources", inventory)

    def test_verifier_reads_only_expected_files_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory) / "repo"
            shutil.copytree(ROOT / "docs" / "legacy-protocol", work / "docs" / "legacy-protocol")
            (work / "tools" / "command-catalog").mkdir(parents=True)
            shutil.copy2(ROOT / "command.py", work / "command.py")
            for name in VerificationExitCodeTests.REFERENCED_SOURCES:
                source = ROOT / name
                if source.is_file() and name != "command.py" and (work / name).exists() is False:
                    shutil.copy2(source, work / name)
            shutil.copy2(ROOT / "tools" / "command-catalog" / "verify_commands.py",
                         work / "tools" / "command-catalog" / "verify_commands.py")
            catalog = json.loads((work / "docs" / "legacy-protocol" / "commands.json").read_text(encoding="utf-8"))
            expected = {"command.py",
                        str(Path("docs") / "legacy-protocol" / "commands.json"),
                        str(Path("docs") / "legacy-protocol" / "commands.md")}
            for reference in catalog["envelope"].get("source_references", []):
                expected.add(reference["file"])
            for entry in catalog["commands"]:
                for reference in entry.get("source_references", []):
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
                    observed.add(str(Path(raw).relative_to(work)))
                except ValueError:
                    self.fail("verifier read outside repo root: %r" % (raw,))
            self.assertEqual(observed, expected)

    def test_no_legacy_module_imports(self):
        source = (ROOT / "tools" / "command-catalog" / "verify_commands.py").read_text(encoding="utf-8")
        for forbidden in ("import flask", "from flask", "import server", "from server",
                          "import sessions", "import command", "from command",
                          "import engine", "from engine",
                          "import requests", "subprocess", "socket", "webbrowser"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
