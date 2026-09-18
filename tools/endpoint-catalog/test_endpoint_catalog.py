import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

import verify_endpoints as verifier

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


class ReadOnlyArgumentsTests(unittest.TestCase):
    def test_report_argument_rejected_without_changing_target(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target.json"
            original = b"preserved input bytes\n"
            target.write_bytes(original)
            with self.assertRaises(SystemExit) as raised:
                run_main(["--report", str(target)])
            self.assertEqual(raised.exception.code, 2)
            self.assertEqual(target.read_bytes(), original)
            self.assertEqual(list(Path(directory).iterdir()), [target])

    def test_report_argument_does_not_create_missing_target(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "missing.json"
            with self.assertRaises(SystemExit) as raised:
                run_main(["--report", str(target)])
            self.assertEqual(raised.exception.code, 2)
            self.assertFalse(target.exists())
            self.assertEqual(list(Path(directory).iterdir()), [])


class RouteExtractionTests(unittest.TestCase):
    def test_current_source_extracts_15_active_registrations(self):
        source = (ROOT / "server.py").read_text(encoding="utf-8")
        registrations = verifier.extract_registrations_with_bindings(source)
        routes = [r["route"] for r in registrations]
        self.assertEqual(len(routes), 15)
        self.assertIn("/dynamic/menvswomen/srvsexwars/command.php", routes)
        self.assertIn("/dynamic/menvswomen/srvsexwars/alliance/", routes)
        commented = [r for r in routes if "/bets/" in r]
        self.assertEqual(commented, [])

    def test_constant_binding_concatenation_resolves(self):
        source = (
            "ROOT = '/dynamic'\n"
            "import something_else\n"
            "@app.route(ROOT + '/example', methods=['POST'])\n"
            "def handler():\n"
            "    return ''\n"
        )
        registrations = verifier.extract_registrations_with_bindings(source)
        self.assertEqual(registrations, [{"route": "/dynamic/example",
                                          "declared_methods": ["POST"],
                                          "function": "handler"}])

    def test_unresolved_name_is_unsupported(self):
        source = "@app.route(UNKNOWN + '/x')\ndef handler():\n    return ''\n"
        with self.assertRaisesRegex(verifier.VerificationError, "unsupported route expression"):
            verifier.extract_registrations_with_bindings(source)

    def test_dynamic_expression_is_unsupported(self):
        source = "@app.route('/x' + str(1))\ndef handler():\n    return ''\n"
        with self.assertRaisesRegex(verifier.VerificationError, "unsupported route expression"):
            verifier.extract_registrations_with_bindings(source)

    def test_declared_and_effective_methods(self):
        source = ("@app.route('/a', methods=['GET', 'POST'])\n"
                  "def a():\n    return ''\n"
                  "@app.route('/b')\n"
                  "def b():\n    return ''\n")
        registrations = verifier.extract_registrations_with_bindings(source)
        self.assertEqual(registrations[0]["declared_methods"], ["GET", "POST"])
        self.assertIsNone(registrations[1]["declared_methods"])
        self.assertEqual(verifier.effective_methods(["GET", "POST"]),
                         ["GET", "HEAD", "OPTIONS", "POST"])
        self.assertEqual(verifier.effective_methods(None),
                         ["GET", "HEAD", "OPTIONS"])


class VerificationExitCodeTests(unittest.TestCase):
    REFERENCED_SOURCES = ("sessions.py", "bundle.py", "get_game_config.py",
                          "get_player_info.py", "command.py",
                          "legacy_command_recorder.py")

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name) / "repo"
        shutil.copytree(ROOT / "docs" / "legacy-protocol", self.work / "docs" / "legacy-protocol")
        (self.work / "tools").mkdir()
        shutil.copy2(ROOT / "server.py", self.work / "server.py")
        for name in self.REFERENCED_SOURCES:
            source = ROOT / name
            if source.is_file():
                shutil.copy2(source, self.work / name)
        shutil.copy2(ROOT / "tools" / "endpoint-catalog" / "verify_endpoints.py",
                     self.work / "tools" / "verify_endpoints.py")

    def copy_tool(self):
        target = self.work / "tools" / "endpoint-catalog"
        target.mkdir()
        shutil.copy2(ROOT / "tools" / "endpoint-catalog" / "verify_endpoints.py",
                     target / "verify_endpoints.py")
        return target

    def load_catalog(self):
        return json.loads((self.work / "docs" / "legacy-protocol" / "endpoints.json").read_text(encoding="utf-8"))

    def save_catalog(self, document):
        (self.work / "docs" / "legacy-protocol" / "endpoints.json").write_text(
            json.dumps(document, indent=2) + "\n", encoding="utf-8")

    def test_agreement_exit_0(self):
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 0)

    def test_route_drift_exit_1(self):
        document = self.load_catalog()
        for entry in document["endpoints"]:
            if entry["route"] == "/null":
                entry["route"] = "/null-renamed"
        self.save_catalog(document)
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 1)

    def test_method_drift_exit_1(self):
        document = self.load_catalog()
        for entry in document["endpoints"]:
            if entry["route"] == "/dynamic/menvswomen/srvsexwars/command.php":
                entry["declared_methods"] = ["GET"]
                entry["effective_methods"] = ["GET", "HEAD", "OPTIONS"]
        self.save_catalog(document)
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 1)

    def test_inventory_drift_exit_1(self):
        inventory = self.work / "docs" / "legacy-protocol" / "endpoints.md"
        text = inventory.read_text(encoding="utf-8")
        inventory.write_text(text.replace("`/null`", "`/gone`"), encoding="utf-8")
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 1)

    def test_disabled_entry_registered_live_exit_1(self):
        server = self.work / "server.py"
        text = server.read_text(encoding="utf-8")
        text += ("\n@app.route('/dynamic/menvswomen/srvsexwars/bets/get_bets_list.php',"
                 " methods=['POST'])\n"
                 "def reenabled_bets_list():\n"
                 "    return ''\n")
        server.write_text(text, encoding="utf-8")
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 1)

    def test_source_reference_out_of_range_exit_2(self):
        document = self.load_catalog()
        sessions = (self.work / "sessions.py").read_text(encoding="utf-8")
        total = len(sessions.splitlines())
        for entry in document["endpoints"]:
            for reference in entry["source_references"]:
                if reference["file"] == "sessions.py":
                    reference["end_line"] = total + 1
                    break
            else:
                continue
            break
        self.save_catalog(document)
        code, stderr = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 2)
        self.assertIn("out of range", stderr)

    def test_invalid_catalog_exit_2(self):
        (self.work / "docs" / "legacy-protocol" / "endpoints.json").write_text("{broken",
                                                                              encoding="utf-8")
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 2)

    def test_unparseable_source_exit_2(self):
        (self.work / "server.py").write_text("def broken(:\n", encoding="utf-8")
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 2)

    def test_missing_files_exit_2(self):
        (self.work / "docs" / "legacy-protocol" / "endpoints.md").unlink()
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 2)


class ConsistencyAndContainmentTests(unittest.TestCase):
    def test_catalog_entries_match_source_counts(self):
        source = (ROOT / "server.py").read_text(encoding="utf-8")
        catalog = json.loads((ROOT / "docs" / "legacy-protocol" / "endpoints.json").read_text(encoding="utf-8"))
        counts = {}
        for entry in catalog["endpoints"]:
            counts[entry["classification"]] = counts.get(entry["classification"], 0) + 1
        self.assertEqual(counts, {"explicit_active": 15, "framework_default": 1, "disabled": 3})
        registrations = verifier.extract_registrations_with_bindings(source)
        self.assertEqual(len(registrations), 15)
        catalog_active = {e["route"] for e in catalog["endpoints"] if e["classification"] == "explicit_active"}
        self.assertEqual(catalog_active, {r["route"] for r in registrations})

    def test_inventory_covers_every_catalog_route(self):
        catalog = json.loads((ROOT / "docs" / "legacy-protocol" / "endpoints.json").read_text(encoding="utf-8"))
        inventory = (ROOT / "docs" / "legacy-protocol" / "endpoints.md").read_text(encoding="utf-8")
        for entry in catalog["endpoints"]:
            self.assertIn(entry["route"], inventory)
        self.assertIn("not implemented", inventory)
        self.assertIn("Disabled declarations", inventory)
        self.assertIn("Framework registration", inventory)

    def test_verifier_reads_only_expected_files_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory) / "repo"
            shutil.copytree(ROOT / "docs" / "legacy-protocol", work / "docs" / "legacy-protocol")
            (work / "tools" / "endpoint-catalog").mkdir(parents=True)
            shutil.copy2(ROOT / "server.py", work / "server.py")
            for name in VerificationExitCodeTests.REFERENCED_SOURCES:
                source = ROOT / name
                if source.is_file():
                    shutil.copy2(source, work / name)
            shutil.copy2(ROOT / "tools" / "endpoint-catalog" / "verify_endpoints.py",
                         work / "tools" / "endpoint-catalog" / "verify_endpoints.py")
            catalog = json.loads((work / "docs" / "legacy-protocol" / "endpoints.json").read_text(encoding="utf-8"))
            expected = {"server.py",
                        str(Path("docs") / "legacy-protocol" / "endpoints.json"),
                        str(Path("docs") / "legacy-protocol" / "endpoints.md")}
            for entry in catalog["endpoints"]:
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
        source = (ROOT / "tools" / "endpoint-catalog" / "verify_endpoints.py").read_text(encoding="utf-8")
        for forbidden in ("import flask", "from flask", "import server", "from server",
                          "import sessions", "import command", "import engine",
                          "import requests", "subprocess", "socket", "webbrowser"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
