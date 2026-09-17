"""Controlled disposable evidence, not historical or general gameplay parity."""
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("protocol_replay", Path(__file__).with_name("protocol_replay.py"))
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)


def controlled_record(commands=None, failure=False):
    before = json.loads((ROOT / "tests/saves/fresh-player.json").read_text(encoding="utf-8"))
    before["unknown"] = {"tuple": [True, 1, 1.0, None, {}, []], "A/~": "retained"}
    if commands is None:
        commands = [[0, "complete_tutorial", [15], [0] * 8],
                    [0, "level_up", [7], [10, 3, -999999, 4, 5, 6, 7, 8]],
                    [0, "ping", [], [0] * 8],
                    [0, "set_variables", [], [0, 1, 2, 3, 4, 5, 6, 7]]]
    envelope = {"first_number": 1, "publishActions": [], "ts": 1,
                "tries": 1, "accessToken": "[REDACTED]", "commands": commands}
    # Controlled expected state, independently express the observed branch rules.
    after = copy.deepcopy(before)
    for index, name, args, resources in commands:
        target = after["maps"][index]
        for key, amount in zip(("xp", "gold", "wood", "oil", "steel"), resources[1:6]):
            target[key] = max(target[key] + amount, 0)
        after["playerInfo"]["cash"] = max(after["playerInfo"]["cash"] + resources[6], 0)
        after["privateState"]["mana"] = max(after["privateState"]["mana"] + resources[7], 0)
        if name == "complete_tutorial" and (args[0] >= 25 or args[0] == 15):
            after["playerInfo"]["completed_tutorial"] = 1
        if name == "level_up":
            if not args:
                break
            target["level"] = args[0]
    return {"schema_version": 1, "request": {"method": "POST", "path": replay.ROUTE},
            "correlation": {"player_id": before["playerInfo"]["pid"]},
            "commands": envelope, "before": before, "after": after,
            "outcome": "failure" if failure else "success",
            "response": {"status": 500, "body": None} if failure else {"status": 200, "body": {"result": "success"}},
            "error": {"type": "IndexError", "phase": "command", "message": replay.ERROR_MESSAGE} if failure else None,
            "extra_metadata": {"accessToken": "METADATA-SECRET", "ordinary": "ignored"}}


def partial_record():
    return controlled_record([[0, "level_up", [3], [0] * 8],
                              [0, "level_up", [], [0, 2, 3, 4, 5, 6, 7, 8]],
                              [0, "level_up", [99], [0] * 8]], True)


def snapshot(directory, focused=False):
    result = {}
    for parent, directories, filenames in os.walk(str(directory)):
        directories[:] = [name for name in directories if name != ".git" and not (focused and Path(parent) == ROOT and name in ("assets", "templates", "stub"))]
        for name in directories:
            result["#directory/" + str((Path(parent) / name).relative_to(directory))] = "directory"
        for name in filenames:
            path = Path(parent) / name
            result[str(path.relative_to(directory))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


class ReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not replay.supported_interpreter():
            raise RuntimeError("Focused replay checks require Windows x64 CPython 3.9.13")
        cls.oracle = replay.verify_oracle()
        cls.complete_repository = snapshot(ROOT)

    @classmethod
    def tearDownClass(cls):
        if snapshot(ROOT) != cls.complete_repository:
            raise AssertionError("Repository bytes changed during the suite")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="socialwars-replay-tests-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.evidence = self.directory / "record.json"
        self.record = controlled_record()
        self.write(self.record)
        self.surrounding = self.directory / "surrounding"
        self.surrounding.mkdir()
        for name in ("runtime.save.json", "recorder.json", "canonical.json", "source.py"):
            (self.surrounding / name).write_bytes(b"UNCHANGED-PRIVATE-SENTINEL")
        self.original_surrounding = snapshot(self.surrounding)
        self.repository = snapshot(ROOT, focused=True)
        self.external_before = set((Path(os.environ["SystemRoot"]) / "Temp").glob("socialwars-replay-*"))
        self.created_directories = []
        original_init = tempfile.TemporaryDirectory.__init__
        def track(temporary, *args, **kwargs):
            original_init(temporary, *args, **kwargs)
            if kwargs.get("prefix") == "socialwars-replay-":
                self.created_directories.append(Path(temporary.name))
        patch = mock.patch.object(tempfile.TemporaryDirectory, "__init__", track)
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(self.assert_contained)

    def assert_contained(self):
        self.assertEqual(snapshot(self.surrounding), self.original_surrounding)
        self.assertEqual(snapshot(ROOT, focused=True), self.repository)
        self.assertEqual(set((Path(os.environ["SystemRoot"]) / "Temp").glob("socialwars-replay-*")), self.external_before)
        self.assertFalse(list(self.directory.rglob("__pycache__")))
        self.assertTrue(all(not directory.exists() for directory in self.created_directories))

    def write(self, record):
        self.evidence.write_bytes(json.dumps(record, ensure_ascii=True, allow_nan=False).encode("ascii"))

    def cli(self, record=None):
        if record is not None:
            self.write(record)
        before = self.evidence.read_bytes()
        stdout, stderr = io.BytesIO(), io.StringIO()
        status = replay.main(["replay", "--record", str(self.evidence)], stdout, stderr)
        self.assertEqual(self.evidence.read_bytes(), before)
        return status, stdout.getvalue(), stderr.getvalue()

    def reject(self, record):
        with mock.patch.object(replay, "verify_oracle", side_effect=AssertionError("provenance must not begin")) as oracle, mock.patch.object(replay, "execute") as child:
            status, output, error = self.cli(record)
        self.assertEqual(status, 2)
        self.assertEqual(output, b"")
        self.assertRegex(error, r"^[a-z ]+\n$")
        oracle.assert_not_called()
        child.assert_not_called()

    def test_success_repeat_report_and_sinks(self):
        with mock.patch.dict(os.environ, {"PYTHONPATH": str(ROOT), "SOCIALWARS_COMMAND_RECORD_DIR": str(self.surrounding), "HTTP_PROXY": "private-secret", "TMP": str(ROOT), "TEMP": str(ROOT)}):
            first = self.cli()
            self.assertEqual(first, self.cli())
        status, output, error = first
        self.assertEqual((status, error), (0, ""))
        report = json.loads(output)
        self.assertEqual(report, {"schema_version": 1, "policy": "legacy-command-replay-v1", "replay": "match", "outcome": "equal", "response": "equal", "persistence": "equal", "state": {"schema_version": 1, "policy": "structural-json-types-v1", "comparison": "equal", "change_count": 0, "changes": []}})
        self.assertEqual(output, replay.diff.serialize_report(report))
        self.assertFalse(set(sys.modules) & {"server", "command", "sessions", "engine", "legacy_command_recorder"})
        for forbidden in (b"COMMAND", b"Pong", b"METADATA-SECRET", str(ROOT).encode(), self.record["correlation"]["player_id"].encode()):
            self.assertNotIn(forbidden, output)

    def test_partial_failure_resource_order_stop_and_clock(self):
        record = replay.validate_record(partial_record())
        one = replay.execute(record, self.oracle, 1)
        two = replay.execute(record, self.oracle, 2147483647)
        self.assertEqual(one, two)
        self.assertEqual(one["state"], record["after"])
        self.assertEqual(one["state"]["maps"][0]["level"], 3)
        self.assertFalse(one["persisted"])
        self.assertIsNone(one["saved_state"])
        self.assertEqual(self.cli(record)[0], 0)

    def test_success_clock_independence_and_real_persistence(self):
        record = replay.validate_record(self.record)
        one = replay.execute(record, self.oracle, -1)
        self.assertEqual(one, replay.execute(record, self.oracle, 99999999))
        self.assertEqual(one["state"], record["after"])
        self.assertEqual(one["saved_state"], one["state"])
        self.assertTrue(one["persisted"])
        self.assertEqual(one["state"]["unknown"], self.record["before"]["unknown"])
        self.assertEqual(one["state"]["playerInfo"]["pid"], self.record["correlation"]["player_id"])

    def test_tutorial_boundaries(self):
        for step, completed in ((14, 0), (15, 1), (24, 0), (25, 1), (26, 1), (-1, 0)):
            record = controlled_record([[0, "complete_tutorial", [step], [0] * 8]])
            record["before"]["playerInfo"]["completed_tutorial"] = 0
            record["after"]["playerInfo"]["completed_tutorial"] = completed
            with self.subTest(step=step):
                self.assertEqual(self.cli(record)[0], 0)

    def test_batch_empty_and_maximum(self):
        for count in (0, 256):
            self.assertEqual(self.cli(controlled_record([[0, "ping", [], [0] * 8]] * count))[0], 0)
        record = controlled_record()
        record["commands"]["commands"] = [[0, "ping", [], [0] * 8]] * 257
        self.reject(record)

    def test_additional_map_and_numeric_deltas(self):
        record = controlled_record([[0, "set_variables", [], [0, 0.5, 1.5, -0.5, 0, 0, 0.5, 0.25]]])
        record["before"]["maps"].append(copy.deepcopy(record["before"]["maps"][0]))
        record["after"]["maps"].append(copy.deepcopy(record["after"]["maps"][0]))
        record["after"]["maps"][0] = copy.deepcopy(record["before"]["maps"][0])
        record["commands"]["commands"][0][0] = 1
        self.assertEqual(self.cli(record)[0], 0)

    def test_state_difference_strict_types_paths_and_unknowns(self):
        record = copy.deepcopy(self.record)
        record["after"]["unknown"]["tuple"] = [1, 1.0, True, [], {}, None]
        record["after"]["unknown"]["A/~"] = "changed"
        record["after"]["unknown"][""] = []
        status, output, error = self.cli(record)
        self.assertEqual((status, error), (1, ""))
        report = json.loads(output)
        self.assertEqual(report["replay"], "different")
        self.assertIn("/unknown/A~1~0", [e["path"] for e in report["state"]["changes"]])
        self.assertIn("/unknown/", [e["path"] for e in report["state"]["changes"]])
        self.assertEqual(report["state"]["change_count"], 7)

    def test_schema_boundaries_route_correlation(self):
        mutations = [
            ("schema_version", True), ("schema_version", 1.0), ("schema_version", 2),
            ("before", None), ("after", None), ("before", []), ("after", "bad"),
            ("commands", []), ("correlation", None), ("outcome", "other"),
            ("response", None), ("error", {}),
        ]
        for key, value in mutations:
            record = copy.deepcopy(self.record)
            record[key] = value
            with self.subTest(key=key, value=value):
                self.reject(record)
        for role in ("before", "after"):
            record = copy.deepcopy(self.record)
            record[role]["playerInfo"]["pid"] = "another"
            self.reject(record)
        for method, path in (("GET", replay.ROUTE), ("POST", "/command.php")):
            record = copy.deepcopy(self.record)
            record["request"] = {"method": method, "path": path}
            self.reject(record)
        for player in (None, 1, "", "prefix[REDACTED]"):
            record = copy.deepcopy(self.record)
            record["correlation"]["player_id"] = player
            self.reject(record)
        for key in self.record["commands"]:
            record = copy.deepcopy(self.record)
            del record["commands"][key]
            self.reject(record)

    def test_command_shapes_and_redaction(self):
        invalid = [None, {}, [], [0, "ping", [], [0] * 8, 1],
                   [True, "ping", [], [0] * 8], [-1, "ping", [], [0] * 8],
                   [1, "ping", [], [0] * 8], [0.0, "ping", [], [0] * 8],
                   [0, "buy", [], [0] * 8], [0, 1, [], [0] * 8],
                   [0, "ping", [1], [0] * 8], [0, "set_variables", [1], [0] * 8],
                   [0, "ping", {}, [0] * 8], [0, "ping", [], [0] * 7],
                   [0, "ping", [], [0] * 9], [0, "ping", [], [True] * 8],
                   [0, "ping", [], ["0"] * 8], [0, "ping", [], None],
                   [0, "level_up", [True], [0] * 8], [0, "level_up", [1.0], [0] * 8],
                   [0, "level_up", ["[REDACTED]"], [0] * 8],
                   [0, "level_up", [1, 2], [0] * 8], [0, "level_up", [], [0] * 8],
                   [0, "complete_tutorial", [], [0] * 8], [0, "complete_tutorial", [1, 2], [0] * 8],
                   [0, "complete_tutorial", ["15"], [0] * 8]]
        for comm in invalid:
            record = copy.deepcopy(self.record)
            record["commands"]["commands"] = [comm]
            with self.subTest(comm=comm):
                self.reject(record)
        for value in (True, "[REDACTED]", None):
            record = copy.deepcopy(self.record)
            record["before"]["maps"][0]["xp"] = value
            self.reject(record)
        for key in ("privateState", "maps", "playerInfo"):
            record = copy.deepcopy(self.record)
            record["before"][key] = []
            self.reject(record)

    def test_failure_and_response_coherence(self):
        for phase in ("parse", "response", "snapshot"):
            record = partial_record()
            record["error"]["phase"] = phase
            self.reject(record)
        for field, value in (("type", "KeyError"), ("message", "secret exception text")):
            record = partial_record()
            record["error"][field] = value
            self.reject(record)
        for status, body in ((True, None), (500.0, None), (200, None), (500, "failure text")):
            record = partial_record()
            record["response"] = {"status": status, "body": body}
            self.reject(record)
        for status, body in ((True, {"result": "success"}), (200.0, {"result": "success"}), (200, None), (500, {"result": "success"})):
            record = copy.deepcopy(self.record)
            record["response"] = {"status": status, "body": body}
            self.reject(record)
        record = partial_record()
        record["commands"]["commands"][1][2] = [2]
        self.reject(record)

    def test_unknown_metadata_and_nonexecuted_redaction(self):
        record = copy.deepcopy(self.record)
        record["commands"]["ignored"] = {"nested": "[REDACTED]"}
        record["before"]["token"] = record["after"]["token"] = "[REDACTED]"
        record["response"]["unknown"] = [1, 2]
        self.assertEqual(self.cli(record)[0], 0)

    def test_strict_json_and_input_limits(self):
        for data in (b'\xff', b'{', b'{"schema_version":1,"schema_version":1}', b'NaN', b'Infinity', b'1e999', b'"\\ud800"'):
            self.evidence.write_bytes(data)
            with mock.patch.object(replay, "execute") as child:
                status, output, error = self.cli()
            self.assertEqual((status, output), (2, b""))
            self.assertNotIn("Traceback", error)
            child.assert_not_called()
        with mock.patch.object(replay.diff, "MAX_INPUT_BYTES", 8):
            self.reject(self.record)
        nested = {}
        for _ in range(129):
            nested = {"child": nested}
        record = copy.deepcopy(self.record)
        record["unknown"] = nested
        self.reject(record)
        with mock.patch.object(replay.diff, "MAX_NODES", 10):
            self.reject(self.record)
        record = copy.deepcopy(self.record)
        record["unknown"] = float("inf")
        with self.assertRaises(replay.diff.DiffError):
            replay.validate_record(record)
        self.evidence.write_bytes(b" " * (replay.diff.MAX_INPUT_BYTES + 1))
        self.assertEqual(self.cli()[0:2], (2, b""))

    def test_invalid_arguments_and_nonregular_evidence(self):
        for args in ([], ["replay"], ["replay", "--before", "SECRET"], ["replay", "--rec", "SECRET"], ["compare"], ["replay", "--record", "A", "--record", "B"]):
            output, error = io.BytesIO(), io.StringIO()
            self.assertEqual(replay.main(args, output, error), 2)
            self.assertEqual(output.getvalue(), b"")
            self.assertEqual(error.getvalue(), "arguments invalid\n")
        for path in (self.directory, self.directory / "absent"):
            output, error = io.BytesIO(), io.StringIO()
            self.assertEqual(replay.main(["replay", "--record", str(path)], output, error), 2)
            self.assertEqual(output.getvalue(), b"")

    def test_oracle_manifest_exact_and_line_endings(self):
        self.assertEqual(set(self.oracle), set(replay.ORACLE_FILES))
        self.assertNotIn("server.py", self.oracle)
        self.assertNotIn("legacy_command_recorder.py", self.oracle)
        self.assertNotIn("mods/no_hiring_needed.json", self.oracle)
        copy_root = self.directory / "oracle"
        copy_root.mkdir()
        for name, data in self.oracle.items():
            target = copy_root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data.replace(b"\r\n", b"\n"))
        original_git = replay.git_bytes
        with mock.patch.object(replay, "git_bytes", side_effect=lambda root, *args: original_git(ROOT, *args)):
            self.assertEqual(set(replay.verify_oracle(copy_root)), set(self.oracle))
            for name, data in self.oracle.items():
                (copy_root / name).write_bytes(data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
            replay.verify_oracle(copy_root)
            (copy_root / "command.py").write_bytes(b"drift")
            with self.assertRaisesRegex(replay.ReplayError, "oracle drift"):
                replay.verify_oracle(copy_root)
            (copy_root / "command.py").unlink()
            with self.assertRaisesRegex(replay.ReplayError, "oracle unavailable"):
                replay.verify_oracle(copy_root)

    def test_oracle_missing_git_bad_blob_and_configured_extra(self):
        with mock.patch.object(replay.shutil, "which", return_value=None):
            self.assertEqual(self.cli()[0:2], (2, b""))
        with mock.patch.object(replay, "git_bytes", return_value=b"0" * 40):
            self.assertEqual(self.cli()[0:2], (2, b""))
        copy_root = self.directory / "oracle"
        copy_root.mkdir()
        for name, data in self.oracle.items():
            target = copy_root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        original_git = replay.git_bytes
        with mock.patch.object(replay, "git_bytes", side_effect=lambda root, *args: original_git(ROOT, *args)):
            for name in ("mods/mods.txt", "config/patch/patches.txt"):
                (copy_root / name).write_bytes(self.oracle[name] + b"\nextra-configured\n")
                with self.assertRaisesRegex(replay.ReplayError, "oracle drift"):
                    replay.verify_oracle(copy_root)
                (copy_root / name).write_bytes(self.oracle[name])
            (copy_root / "command.py").unlink()
            os.link(str(copy_root / "engine.py"), str(copy_root / "command.py"))
            with self.assertRaisesRegex(replay.ReplayError, "oracle unavailable"):
                replay.verify_oracle(copy_root)

    def test_linked_oracle_directory_junction(self):
        source = self.directory / "actual"
        source.mkdir()
        (source / "main.json").write_bytes(self.oracle["config/main.json"])
        linked = self.directory / "linked"
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(linked), str(source)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0)
        try:
            with self.assertRaisesRegex(replay.ReplayError, "oracle unavailable"):
                replay.regular_unlinked(linked / "main.json", self.directory)
        finally:
            os.rmdir(str(linked))

    def test_combined_secrets_protection_and_collision(self):
        result = replay.execute(self.record, self.oracle)
        result["state"]["token"] = "ACTUAL-SECRET"
        result["saved_state"]["token"] = "ACTUAL-SECRET"
        for state in (result["state"], result["saved_state"]):
            state["unknown"]["prefix-ACTUAL-SECRET/~"] = 1
        report = replay.make_report(self.record, result)
        data = replay.diff.serialize_report(report)
        self.assertNotIn(b"ACTUAL-SECRET", data)
        self.assertIn(b"prefix-[REDACTED]~1~0", data)
        self.record["after"]["METADATA-SECRET"] = 1
        self.record["after"]["[REDACTED]"] = 1
        with self.assertRaisesRegex(replay.diff.DiffError, "comparison path ambiguity"):
            replay.make_report(self.record, result)
        with mock.patch.object(replay, "execute", return_value=result):
            self.assertEqual(self.cli(self.record), (2, b"", "comparison path ambiguity\n"))

    def test_all_comparison_axes(self):
        result = replay.execute(self.record, self.oracle)
        for field, value in (("outcome", "IndexError"), ("response", {"status": 500, "body": None}), ("persisted", False)):
            changed = copy.deepcopy(result)
            changed[field] = value
            if field == "persisted":
                changed["saved_state"] = None
            report = replay.make_report(self.record, changed)
            self.assertEqual(report["replay"], "different")
            self.assertEqual(report["persistence" if field == "persisted" else field], "different")
            with mock.patch.object(replay, "execute", return_value=changed):
                self.assertEqual(self.cli()[0], 1)

    def test_comparison_limits_and_persistence_inconsistency(self):
        result = replay.execute(self.record, self.oracle)
        record = copy.deepcopy(self.record)
        record["after"]["new"] = 1
        with mock.patch.object(replay.diff, "MAX_CHANGES", 0), mock.patch.object(replay, "execute", return_value=result):
            self.assertEqual(self.cli(record), (2, b"", "replay limit exceeded\n"))
        result["saved_state"]["unknown"] = None
        with mock.patch.object(replay, "execute", return_value=result):
            self.assertEqual(self.cli(self.record), (2, b"", "persistence failed\n"))

    def test_real_child_dependency_unexpected_exception_persistence_failures(self):
        variants = []
        dependency = dict(self.oracle)
        dependency["get_game_config.py"] = b"raise ImportError('PRIVATE-FAILURE')\n"
        variants.append((dependency, "dependency failed"))
        unexpected = dict(self.oracle)
        unexpected["command.py"] += b"\ndef command(*args):\n    raise ValueError('PRIVATE-FAILURE')\n"
        variants.append((unexpected, "legacy failed"))
        persist = dict(self.oracle)
        persist["sessions.py"] += b"\ndef save_session(*args):\n    raise OSError('PRIVATE-FAILURE')\n"
        variants.append((persist, "persistence failed"))
        absent = dict(self.oracle)
        absent["sessions.py"] += b"\ndef save_session(*args):\n    pass\n"
        variants.append((absent, "persistence failed"))
        for oracle, category in variants:
            with mock.patch.object(replay, "verify_oracle", return_value=oracle):
                self.assertEqual(self.cli(), (2, b"", category + "\n"))

    def test_child_forbidden_services_imports_and_writes(self):
        for statement in ("import server", "import legacy_command_recorder", "import socket; socket.socket()", "import subprocess; subprocess.Popen(['cmd'])", "import os; os.startfile('https://invalid.example')", "open('../outside', 'w').write('secret')"):
            oracle = dict(self.oracle)
            oracle["command.py"] += ("\ndef command(*args):\n    " + statement + "\n").encode("ascii")
            with mock.patch.object(replay, "verify_oracle", return_value=oracle):
                self.assertEqual(self.cli()[0:2], (2, b""))
        oracle = dict(self.oracle)
        # A loader or migration call would raise; regular dispatch must succeed.
        oracle["sessions.py"] += b"\ndef load_saves():\n    raise AssertionError()\ndef load_static_villages():\n    raise AssertionError()\ndef load_quests():\n    raise AssertionError()\n"
        oracle["version.py"] += b"\ndef migrate_loaded_save(*args):\n    raise AssertionError()\n"
        self.assertEqual(replay.execute(self.record, oracle)["state"], self.record["after"])

    def test_child_timeout_crash_oversized_malformed_and_reaped(self):
        for script, category in (("import time; time.sleep(10)", "child timeout"),
                                 ("import os; os._exit(9)", "child failed"),
                                 ("print('x' * 4096)", "replay limit exceeded"),
                                 ("print('PRIVATE-MALFORMED')", "child failed"),
                                 ("print('{}')", None)):
            directory = self.directory / "child"
            directory.mkdir(exist_ok=True)
            (directory / "replay_child.py").write_text(script, encoding="ascii")
            children = []
            popen = replay.subprocess.Popen
            def track(*args, **kwargs):
                process = popen(*args, **kwargs)
                children.append(process)
                self.assertEqual(args[0][1:3], ["-I", "-B"])
                self.assertEqual(set(kwargs["env"]) - {"SystemRoot", "WINDIR"}, set())
                return process
            with mock.patch.object(replay.subprocess, "Popen", side_effect=track), mock.patch.object(replay, "CHILD_TIMEOUT", 0.3), mock.patch.object(replay, "MAX_RESULT_BYTES", 1024):
                if category:
                    with self.assertRaisesRegex(replay.ReplayError, category):
                        replay.run_child(directory)
                else:
                    self.assertEqual(replay.run_child(directory), {})
            self.assertTrue(children)
            self.assertTrue(all(c.poll() is not None for c in children))
            self.assertTrue(all(c.stdout.closed for c in children))

    def test_real_child_result_limit_and_launch_failure(self):
        with mock.patch.object(replay, "MAX_RESULT_BYTES", 16):
            self.assertEqual(self.cli(), (2, b"", "replay limit exceeded\n"))
        with mock.patch.object(replay.subprocess, "Popen", side_effect=OSError("PRIVATE-LAUNCH")):
            with self.assertRaisesRegex(replay.ReplayError, "child unavailable"):
                replay.run_child(self.directory)
        with mock.patch.object(replay, "supported_interpreter", return_value=False):
            self.assertEqual(self.cli(), (2, b"", "interpreter unsupported\n"))

    def test_cleanup_failures_no_report_and_real_cleanup(self):
        original_cleanup = tempfile.TemporaryDirectory.cleanup
        def fail_after_cleanup(temporary):
            original_cleanup(temporary)
            raise OSError("PRIVATE-CLEANUP")
        with mock.patch.object(tempfile.TemporaryDirectory, "cleanup", fail_after_cleanup):
            self.assertEqual(self.cli(), (2, b"", "cleanup failed\n"))

    def test_serialization_and_output_failures(self):
        result = replay.execute(self.record, self.oracle)
        with mock.patch.object(replay, "execute", return_value=result), mock.patch.object(replay.diff, "serialize_report", side_effect=replay.diff.DiffError("report serialization failed")):
            self.assertEqual(self.cli(), (2, b"", "report serialization failed\n"))
        class Broken:
            def write(self, data):
                raise OSError("PRIVATE-OUTPUT")
            def flush(self):
                raise OSError("PRIVATE-FLUSH")
        class Short:
            def write(self, data):
                return 0
            def flush(self):
                pass
        class Flush:
            def write(self, data):
                return len(data)
            def flush(self):
                raise OSError()
        for sink in (Broken(), Short(), Flush()):
            with mock.patch.object(replay, "execute", return_value=result):
                diagnostic = io.StringIO()
                self.assertEqual(replay.main(["replay", "--record", str(self.evidence)], sink, diagnostic), 2)
                self.assertEqual(diagnostic.getvalue(), "output failed\n")
                self.assertEqual(replay.main(["replay", "--record", str(self.evidence)], sink, Broken()), 2)

    def test_cli_subprocess_report_no_shutdown_diagnostic(self):
        command = [sys.executable, "-B", str(Path(__file__).with_name("protocol_replay.py")), "replay", "--record", str(self.evidence)]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(json.loads(result.stdout)["replay"], "match")
        self.evidence.write_bytes(b"PRIVATE-INVALID")
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (2, b"", b"record invalid\n"))

    def test_complete_input_and_comparison_limit_edges(self):
        record = copy.deepcopy(self.record)
        record["unknown"] = "unchanged metadata"
        # Limit accounting comes directly from the existing core, across roots.
        with mock.patch.object(replay.diff, "MAX_NODES", 1_000_000):
            replay.diff.inspect_inputs([([None] * 999999, "record")])
            with self.assertRaises(replay.diff.DiffError):
                replay.diff.inspect_inputs([([None] * 1000000, "record")])
        nested = None
        for _ in range(128):
            nested = [nested]
        replay.diff.inspect_inputs([(nested, "record")])
        with self.assertRaises(replay.diff.DiffError):
            replay.diff.inspect_inputs([([nested], "record")])
        changes = replay.diff.structural_changes({}, {str(i): None for i in range(100000)})
        self.assertEqual(len(changes), 100000)
        with self.assertRaises(replay.diff.DiffError):
            replay.diff.structural_changes({}, {str(i): None for i in range(100001)})
        self.evidence.write_bytes(b" " * (replay.diff.MAX_INPUT_BYTES - 2) + b"{}")
        self.assertEqual(replay.diff.load_input(str(self.evidence), "record"), {})

    def test_manifest_adversaries_and_git_content_digest(self):
        load = replay.diff.load_input
        manifest = load(str(Path(__file__).with_name("oracle-manifest.json")), "oracle")
        for change in ("root", "baseline", "extra", "version", "size", "blob"):
            altered = copy.deepcopy(manifest)
            if change == "root":
                altered = []
            elif change == "baseline":
                altered["baseline"] = "0" * 40
            elif change == "extra":
                altered["files"]["server.py"] = {"size": 1, "blob": "0" * 40}
            elif change == "version":
                altered["schema_version"] = True
            elif change == "size":
                altered["files"]["bundle.py"]["size"] = True
            else:
                altered["files"]["bundle.py"]["blob"] = "0" * 40
            with mock.patch.object(replay.diff, "load_input", return_value=altered):
                with self.assertRaisesRegex(replay.ReplayError, "oracle drift"):
                    replay.verify_oracle()
        git = replay.git_bytes
        def corrupted(root, *args):
            data = git(root, *args)
            return (b"!" + data[1:]) if args[0] == "cat-file" else data
        with mock.patch.object(replay, "git_bytes", side_effect=corrupted):
            with self.assertRaisesRegex(replay.ReplayError, "oracle drift"):
                replay.verify_oracle()

    def test_player_alias_and_readonly_ambient_save_isolation(self):
        record = controlled_record([[0, "ping", [], [0] * 8]])
        player = "../../PRIVATE-PATH-PLAYER"
        record["correlation"]["player_id"] = player
        for role in ("before", "after"):
            record[role]["playerInfo"]["pid"] = player
        self.assertEqual(self.cli(record)[0], 0)
        # A known ambient filename is inaccessible even in the child save root.
        oracle = dict(self.oracle)
        oracle["command.py"] += b"\ndef command(*args):\n    open('saves/ambient.save.json').read()\n"
        with mock.patch.object(replay, "verify_oracle", return_value=oracle):
            self.assertEqual(self.cli(record)[0:2], (2, b""))

    def test_player_paths_are_private_and_default_bounds_are_fixed(self):
        self.assertEqual((replay.CHILD_TIMEOUT, replay.MAX_RESULT_BYTES, replay.MAX_COMMANDS), (30, 32 * 1024 * 1024, 256))
        result = replay.execute(self.record, self.oracle)
        player = self.record["correlation"]["player_id"]
        self.record["after"]["unknown"]["player-" + player] = None
        report = replay.make_report(self.record, result)
        data = replay.diff.serialize_report(report)
        self.assertNotIn(player.encode("ascii"), data)
        self.assertIn(b"player-[REDACTED]", data)

    def test_missing_comparison_dependency_has_no_import_traceback(self):
        directory = self.directory / "missing-core/tools/protocol-replay"
        directory.mkdir(parents=True)
        script = directory / "protocol_replay.py"
        script.write_bytes(Path(__file__).with_name("protocol_replay.py").read_bytes())
        result = subprocess.run([sys.executable, "-B", str(script), "replay", "--record", str(self.evidence)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (2, b"", b"dependency failed\n"))

    def test_unsupported_architecture_is_rejected_before_disposable_execution(self):
        with mock.patch.object(replay.platform, "machine", return_value="ARM64"):
            self.assertFalse(replay.supported_interpreter())
            self.assertEqual(self.cli(), (2, b"", "interpreter unsupported\n"))
        self.assertEqual(self.created_directories, [])


if __name__ == "__main__":
    unittest.main()
