"""Controlled route tests: no server startup, browser, or runtime saves."""
import ast
import copy
import io
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import legacy_command_recorder as recorder
from flask import Flask, request
import sessions
from command import command


class RecorderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="socialwars-recorder-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.evidence = self.directory / "evidence"
        self.saves = self.directory / "saves"
        self.saves.mkdir()
        self.fixture = json.loads((ROOT / "tests/saves/fresh-player.json").read_text())
        self.player = self.fixture["playerInfo"]["pid"]
        self.fixture["unrecognized"] = {"nested": [1, {"value": "preserved"}]}
        self.env = mock.patch.dict(os.environ, {}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        os.environ.pop(recorder.DESTINATION_ENV, None)
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(sessions, "SAVES_DIR", str(self.saves)).start()
        self.app = Flask(__name__)
        self.app.testing = True
        # Compile the actual route body without server.py's startup side effects.
        tree = ast.parse((ROOT / "server.py").read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == "command_response")
        node = copy.deepcopy(node)
        node.decorator_list = []
        self.namespace = {"request": request, "json": json, "command": command,
                          "Observation": recorder.Observation, "player_state": sessions.session}
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(ROOT / "server.py"), "exec"), self.namespace)
        self.app.add_url_rule("/dynamic/menvswomen/srvsexwars/command.php", view_func=self.namespace["command_response"], methods=["POST"])
        self.reset()

    def reset(self):
        sessions.__dict__["__saves"] = {self.player: copy.deepcopy(self.fixture)}
        sessions.save_session(self.player)

    def payload(self):
        return {"first_number": 1, "publishActions": [], "ts": 1700000000,
                "tries": 1, "accessToken": "PAYLOAD-TOKEN-SECRET",
                "commands": [[0, "complete_tutorial", [15], [0] * 8],
                             [0, "complete_tutorial", [25], [0] * 8]],
                "extra": {"User_Key": "NESTED-SECRET", "ordinary": "PAYLOAD-TOKEN-SECRET"}}

    def invoke(self, data=None):
        values = {"USERID": self.player, "user_key": "FORM-SECRET", "language": "en",
                  "data": "S" * 64 + ";" + json.dumps(self.payload())}
        if data is not None:
            values["data"] = data
        with self.app.test_request_context("/dynamic/menvswomen/srvsexwars/command.php", method="POST", data=values,
                headers={"Authorization": "Bearer HEADER-SECRET", "Cookie": "session=COOKIE-SECRET"}):
            return self.namespace["command_response"]()

    def records(self):
        return [json.loads(p.read_text()) for p in self.evidence.glob("*.json")]

    def save_bytes(self):
        return (self.saves / (self.player + ".save.json")).read_bytes()

    def enable(self):
        os.environ[recorder.DESTINATION_ENV] = str(self.evidence)

    def test_disabled_is_inert(self):
        with mock.patch.object(recorder.copy, "deepcopy", side_effect=AssertionError("snapshot")), mock.patch.object(recorder, "persist", side_effect=AssertionError("write")):
            self.assertEqual(self.invoke(), ({"result": "success"}, 200))
        self.assertFalse(self.evidence.exists())

    def test_flask_http_response_and_missing_field_status(self):
        self.enable()
        client = self.app.test_client()
        values = {"USERID": self.player, "user_key": "FORM-SECRET", "language": "en",
                  "data": "S" * 64 + ";" + json.dumps(self.payload())}
        response = client.post("/dynamic/menvswomen/srvsexwars/command.php", data=values)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"result": "success"})
        del values["language"]
        response = client.post("/dynamic/menvswomen/srvsexwars/command.php", data=values)
        self.assertEqual(response.status_code, 400)
        failure, = [r for r in self.records() if r["outcome"] == "failure"]
        self.assertEqual(failure["response"], {"status": 400, "body": None})

    def test_success_complete_states_credentials_and_save_parity(self):
        expected = self.invoke()
        expected_bytes = self.save_bytes()
        self.reset()
        before = copy.deepcopy(sessions.session(self.player))
        self.enable()
        self.assertEqual(self.invoke(), expected)
        self.assertEqual(self.save_bytes(), expected_bytes)
        record, = self.records()
        self.assertEqual(record["before"], before)
        self.assertEqual(record["after"], sessions.session(self.player))
        self.assertEqual(record["commands"], recorder.sanitize(self.payload(), recorder.secret_values(self.payload())))
        self.assertEqual(record["response"], {"status": 200, "body": {"result": "success"}})
        self.assertEqual(record["outcome"], "success")
        self.assertEqual(record["schema_version"], 1)
        self.assertEqual(record["correlation"], {"player_id": self.player})
        self.assertGreaterEqual(record["duration_seconds"], 0)
        serialized = json.dumps(record)
        for secret in ("FORM-SECRET", "PAYLOAD-TOKEN-SECRET", "NESTED-SECRET", "HEADER-SECRET", "COOKIE-SECRET", "S" * 64):
            self.assertNotIn(secret, serialized)
        self.assertEqual(len(list(self.evidence.iterdir())), 1)

    def test_parse_failures_preserve_exception_and_save(self):
        original = self.save_bytes()
        self.enable()
        for malformed, error in (("short", IndexError), ("S" * 64 + ":{}", AssertionError), ("S" * 64 + ";{", json.JSONDecodeError)):
            with self.assertRaises(error):
                self.invoke(malformed)
        self.assertEqual(self.save_bytes(), original)
        self.assertEqual(len(self.records()), 3)
        for record in self.records():
            self.assertEqual(record["before"], self.fixture)
            self.assertEqual(record["after"], self.fixture)
            self.assertEqual(record["error"]["phase"], "parse")
            self.assertEqual(record["response"], {"status": 500, "body": None})

    def test_command_failure_captures_partial_mutation_without_save(self):
        original = self.save_bytes()
        failure = ValueError("PAYLOAD-TOKEN-SECRET")
        def fail(player, data):
            sessions.session(player)["unrecognized"]["nested"].append("partial")
            raise failure
        self.namespace["command"] = fail
        self.enable()
        with self.assertRaises(ValueError) as caught:
            self.invoke()
        self.assertIs(caught.exception, failure)
        self.assertEqual(self.save_bytes(), original)
        record, = self.records()
        self.assertEqual(record["before"], self.fixture)
        self.assertEqual(record["after"], sessions.session(self.player))
        self.assertNotIn("PAYLOAD-TOKEN-SECRET", json.dumps(record))

    def test_internal_failures_are_visible_and_preserve_save(self):
        expected = self.invoke()
        saved = self.save_bytes()
        for target in ("persist", "sanitize", "copy.deepcopy"):
            self.reset()
            self.enable()
            with mock.patch("legacy_command_recorder." + target, side_effect=OSError("SECRET")), self.assertLogs(recorder.__name__, level="WARNING") as logs:
                self.assertEqual(self.invoke(), expected)
            self.assertEqual(self.save_bytes(), saved)
            self.assertNotIn("SECRET", " ".join(logs.output))

    def test_diagnostic_failure_fallback_and_exception_parity(self):
        self.enable()
        failure = RuntimeError("original")
        self.namespace["command"] = mock.Mock(side_effect=failure)
        with mock.patch.object(recorder, "persist", side_effect=OSError), mock.patch.object(recorder.logging.Logger, "warning", side_effect=OSError), mock.patch.object(recorder.sys, "stderr", new=io.StringIO()) as stream:
            with self.assertRaises(RuntimeError) as caught:
                self.invoke()
            self.assertIs(caught.exception, failure)
            self.assertIn("recorder", stream.getvalue())
        with mock.patch.object(recorder, "persist", side_effect=OSError), mock.patch.object(recorder.logging.Logger, "warning", side_effect=OSError), mock.patch.object(recorder.sys, "stderr") as stream:
            stream.write.side_effect = OSError
            with self.assertRaises(RuntimeError) as caught:
                self.invoke()
            self.assertIs(caught.exception, failure)

    def test_unsafe_destinations_fail_open(self):
        for destination in (ROOT, ROOT / "saves/recorder", ROOT.parent, Path("relative")):
            with self.assertRaises(ValueError):
                recorder.validate_destination(destination)
            os.environ[recorder.DESTINATION_ENV] = str(destination)
            with self.assertLogs(recorder.__name__, level="WARNING"):
                self.assertEqual(self.invoke(), ({"result": "success"}, 200))
        ordinary_file = self.directory / "file"
        ordinary_file.write_text("untouched")
        with self.assertRaises(ValueError):
            recorder.validate_destination(ordinary_file)
        self.assertEqual(ordinary_file.read_text(), "untouched")

    def test_atomic_multiple_writes_containment_and_cleanup(self):
        self.evidence.mkdir()
        marker = self.evidence / "unrelated"
        marker.write_bytes(b"opaque")
        original_replace = recorder.os.replace
        observed = []
        def replace(source, target):
            self.assertEqual(Path(source).parent, self.evidence)
            self.assertEqual(Path(target).parent, self.evidence)
            self.assertFalse(Path(target).exists())
            observed.append(json.loads(Path(source).read_text()))
            original_replace(source, target)
        with mock.patch.object(recorder.os, "replace", side_effect=replace):
            paths = [recorder.persist(self.evidence, {"record_id": "repeated", "n": n}) for n in range(10)]
        self.assertEqual(len(set(paths)), 10)
        self.assertEqual(len(observed), 10)
        self.assertEqual(marker.read_bytes(), b"opaque")
        self.assertFalse(list(self.evidence.glob("*.tmp")))
        self.assertFalse(list(self.evidence.glob("*.claim")))
        with mock.patch.object(recorder.os, "replace", side_effect=OSError):
            with self.assertRaises(OSError):
                recorder.persist(self.evidence, {"n": 11})
        self.assertEqual(len(list(self.evidence.iterdir())), 11)
        with self.assertRaises(TypeError):
            recorder.persist(self.evidence, {"unserializable": object()})
        self.assertEqual(len(list(self.evidence.iterdir())), 11)

    def test_collision_retry_preserves_existing_evidence(self):
        self.evidence.mkdir()
        existing = self.evidence / ("a" * 32 + ".json")
        existing.write_bytes(b"prior evidence")
        ids = [mock.Mock(hex="a" * 32), mock.Mock(hex="b" * 32)]
        with mock.patch.object(recorder.uuid, "uuid4", side_effect=ids):
            written = recorder.persist(self.evidence, {"n": 1})
        self.assertEqual(existing.read_bytes(), b"prior evidence")
        self.assertEqual(written.name, "b" * 32 + ".json")

    def test_concurrent_writes(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            paths = list(pool.map(lambda n: recorder.persist(self.evidence, {"n": n}), range(20)))
        self.assertEqual(len(set(paths)), 20)
        self.assertEqual({json.loads(p.read_text())["n"] for p in paths}, set(range(20)))
        self.assertEqual(len(list(self.evidence.iterdir())), 20)

    def test_real_command_order_and_failure_parity(self):
        payload = self.payload()
        payload["commands"] = [[0, "level_up", [2], [0] * 8],
                               [0, "level_up", [], [0] * 8]]
        raw = "S" * 64 + ";" + json.dumps(payload)
        original = self.save_bytes()
        with self.assertRaises(IndexError):
            self.invoke(raw)
        expected_state = copy.deepcopy(sessions.session(self.player))
        self.assertEqual(expected_state["maps"][0]["level"], 2)
        self.assertEqual(self.save_bytes(), original)
        for failed_recorder in (False, True):
            self.reset()
            self.enable()
            with mock.patch.object(recorder, "persist", side_effect=OSError) if failed_recorder else mock.patch.object(recorder, "persist", wraps=recorder.persist):
                with self.assertRaises(IndexError):
                    self.invoke(raw)
            self.assertEqual(sessions.session(self.player), expected_state)
            self.assertEqual(self.save_bytes(), original)
        record, = self.records()
        self.assertEqual(record["before"], self.fixture)
        self.assertEqual(record["after"], expected_state)

    def test_resolved_link_into_repository_is_rejected(self):
        linked = self.directory / "repository-link"
        if os.name == "nt":
            subprocess.run(["cmd", "/c", "mklink", "/J", str(linked), str(ROOT)],
                           check=True, capture_output=True)
        else:
            linked.symlink_to(ROOT, target_is_directory=True)
        try:
            with self.assertRaises(ValueError):
                recorder.validate_destination(linked / "recorder-output")
        finally:
            if os.name == "nt":
                os.rmdir(str(linked))  # Remove only the junction, never its target.
            else:
                linked.unlink()


if __name__ == "__main__":
    unittest.main()
