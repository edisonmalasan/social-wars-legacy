"""Controlled focused tests; canonical fixtures are read-only evidence."""

import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import state_diff as diff

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools/state-diff/state_diff.py"
PRE = ROOT / "tests/saves/fresh-player-pre-migration.json"
POST = ROOT / "tests/saves/fresh-player.json"


def snapshot(root):
    return {str(path.relative_to(root)): ("directory" if path.is_dir() else
            hashlib.sha256(path.read_bytes()).hexdigest())
            for path in root.rglob("*")}


def entry(operation, path, before, after):
    return {"operation": operation, "path": path,
            "before_type": before, "after_type": after}


class StateDiffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preserved = {path: path.read_bytes() for path in
                         list(ROOT.glob("*.py")) + list((ROOT / "tests/saves").rglob("*"))
                         if path.is_file()}
        cls.runtime = snapshot(ROOT / "saves")
        cls.runtime_existed = (ROOT / "saves").exists()

    @classmethod
    def tearDownClass(cls):
        if cls.preserved != {path: path.read_bytes() for path in cls.preserved}:
            raise AssertionError("repository source or canonical evidence changed")
        if cls.runtime != snapshot(ROOT / "saves") or cls.runtime_existed != (ROOT / "saves").exists():
            raise AssertionError("runtime saves changed")

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)

    def write(self, name, value):
        path = self.folder / name
        path.write_text(json.dumps(value, ensure_ascii=True), encoding="utf-8")
        return str(path)

    def invoke(self, args, cwd=None):
        original = snapshot(self.folder)
        result = subprocess.run([sys.executable, "-B", str(TOOL)] + args,
                                cwd=str(cwd or self.folder), capture_output=True,
                                timeout=30)
        self.assertEqual(snapshot(self.folder), original)
        return result

    def pair_args(self, before, after):
        return ["compare", "--before", self.write("before.json", before),
                "--after", self.write("after.json", after)]

    def assert_failure(self, result, category=None):
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")
        self.assertLessEqual(len(result.stderr), 80)
        self.assertNotIn(b"Traceback", result.stderr)
        if category:
            self.assertEqual(result.stderr, (category + "\n").encode())

    def test_canonical_version_evidence(self):
        original = {path: path.read_bytes() for path in (PRE, POST)}
        result = self.invoke(["compare", "--before", str(PRE), "--after", str(POST)])
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(json.loads(result.stdout)["changes"],
                         [entry("changed", "/version", "null", "string")])
        self.assertEqual(original, {path: path.read_bytes() for path in original})

    def test_equal_pair_schema_and_lf_serialization(self):
        result = self.invoke(self.pair_args({"unknown": [1, None, {}]}, {"unknown": [1, None, {}]}))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        report = json.loads(result.stdout)
        self.assertEqual(report, {"schema_version": 1, "policy": "structural-json-types-v1",
                                 "comparison": "equal", "change_count": 0, "changes": []})
        self.assertEqual(result.stdout, diff.serialize_report(report))
        self.assertNotIn(b"\r", result.stdout)
        self.assertTrue(result.stdout.endswith(b"\n"))
        self.assertFalse(result.stdout.endswith(b"\n\n"))

    def test_explicit_record_ignores_metadata_for_equality(self):
        record = {"schema_version": 1, "before": {"before": 7, "after": []},
                  "after": {"before": 7, "after": []}, "unknown": {"future": True}}
        result = self.invoke(["compare", "--record", self.write("record.json", record)])
        pair = self.invoke(self.pair_args(record["before"], record["after"]))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, pair.stdout)
        self.assertEqual(result.stderr, b"")

    def test_failed_record_boundaries_are_compared_without_persistence_claim(self):
        record = {"schema_version": 1, "before": {"coins": 5}, "after": {"coins": 4},
                  "outcome": "command_failed", "response": None}
        result = self.invoke(["compare", "--record", self.write("record.json", record)])
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["changes"],
                         [entry("changed", "/coins", "integer", "integer")])

    def test_invalid_arguments_are_categorical(self):
        for args in ([], ["compare"], ["compare", "--before", "PRIVATE"],
                     ["compare", "--record", "PRIVATE", "--before", "PRIVATE"],
                     ["compare", "--record", "PRIVATE", "--after", "PRIVATE"],
                     ["compare", "--unknown=PRIVATE"], ["PRIVATE"],
                     ["compare", "--bef", "PRIVATE", "--after", "PRIVATE"]):
            with self.subTest(args=args):
                self.assert_failure(self.invoke(args), "arguments invalid")

    def test_unavailable_record_evidence(self):
        for before, after in ((None, {}), ({}, None), (None, None)):
            record = {"schema_version": 1, "before": before, "after": after}
            self.assert_failure(self.invoke(["compare", "--record", self.write("r.json", record)]),
                                "record evidence unavailable")
        self.assert_failure(self.invoke(["compare", "--record", self.write("r.json", {"schema_version": 1})]),
                            "record evidence unavailable")

    def test_schema_requires_exact_integer_one(self):
        for version in (True, False, 1.0, "1", None, 0, 2):
            record = {"schema_version": version, "before": {}, "after": {}}
            self.assert_failure(self.invoke(["compare", "--record", self.write("r.json", record)]),
                                "record schema invalid")
        for record in ([], None, {}, {"before": {}, "after": {}}):
            self.assert_failure(self.invoke(["compare", "--record", self.write("r.json", record)]),
                                "record schema invalid")

    def test_object_boundaries_required(self):
        for value in ([], True, 1, "PRIVATE", None):
            self.assert_failure(self.invoke(self.pair_args(value, {})), "before boundary invalid")
            self.assert_failure(self.invoke(self.pair_args({}, value)), "after boundary invalid")
        for value in ([], True, 1, "PRIVATE"):
            record = {"schema_version": 1, "before": {}, "after": value}
            self.assert_failure(self.invoke(["compare", "--record", self.write("r.json", record)]),
                                "record boundary invalid")

    def test_strict_invalid_json_utf8_duplicates_nonfinite_and_unicode(self):
        good = self.write("good.json", {})
        bad = self.folder / "PRIVATE.json"
        samples = (b'PRIVATE', b'{"PRIVATE":}', b'{"PRIVATE": "\xff"}',
                   b'{"PRIVATE": 1, "PRIVATE": 2}', b'{"nested":{"x":1,"x":2}}',
                   b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}',
                   b'{"x":1e9999}', b'{"x":-1e9999}', b'{"x":"\\ud800"}',
                   b'{"\\udfff":1}', b'\xef\xbb\xbf{}', b'{} {}')
        for role in ("before", "after", "record"):
            for data in samples:
                with self.subTest(role=role, data=data):
                    supplied = (b'{"schema_version":1,"before":{},"after":{},"extra":' + data + b'}'
                                if role == "record" else data)
                    bad.write_bytes(supplied)
                    args = ["compare", "--record", str(bad)] if role == "record" else [
                        "compare", "--before", str(bad) if role == "before" else good,
                        "--after", str(bad) if role == "after" else good]
                    self.assert_failure(self.invoke(args), role + " input invalid")

    def test_read_failures_and_nonregular_inputs(self):
        good = self.write("good.json", {})
        for bad in (str(self.folder / "PRIVATE-missing"), str(self.folder)):
            self.assert_failure(self.invoke(["compare", "--before", bad, "--after", good]),
                                "before input read failed")

    def test_byte_limit_exact_boundary_and_overflow(self):
        before = self.folder / "large.json"
        good = self.write("good.json", {})
        before.write_bytes(b"{}" + b" " * (diff.MAX_INPUT_BYTES - 2))
        self.assertEqual(self.invoke(["compare", "--before", str(before), "--after", good]).returncode, 0)
        with before.open("ab") as target:
            target.write(b" ")
        self.assert_failure(self.invoke(["compare", "--before", str(before), "--after", good]),
                            "before input limit exceeded")

    def test_missing_null_empty_subtrees_and_unknown_fields(self):
        report = diff.compare_states({"remove": {"deep": [1]}, "replace": {}, "null": None},
                                     {"add": {"unknown": []}, "replace": [], "NULL": None})
        self.assertEqual(report["changes"], [entry("added", "/NULL", "missing", "null"),
            entry("added", "/add", "missing", "object"), entry("removed", "/null", "null", "missing"),
            entry("removed", "/remove", "object", "missing"), entry("changed", "/replace", "object", "array")])

    def test_strict_scalar_types_and_value_free_entries(self):
        before = {"a": True, "b": 1, "c": 1.0, "d": None, "e": "PRIVATE-old"}
        after = {"a": 1, "b": 1.0, "c": True, "d": "PRIVATE-null", "e": "PRIVATE-new"}
        report = diff.compare_states(before, after)
        self.assertEqual([e["before_type"] for e in report["changes"]],
                         ["boolean", "integer", "number", "null", "string"])
        self.assertEqual([e["after_type"] for e in report["changes"]],
                         ["integer", "number", "boolean", "string", "string"])
        self.assertEqual(report["change_count"], 5)
        self.assertNotIn(b"PRIVATE", diff.serialize_report(report))
        self.assertTrue(all(set(e) == {"operation", "path", "before_type", "after_type"}
                            for e in report["changes"]))

    def test_numeric_string_keys_case_and_rfc6901(self):
        keys = ("10", "2", "A", "a", "a/b", "a~b", "", "\u00e9")
        report = diff.compare_states({}, {key: None for key in keys})
        self.assertEqual([e["path"] for e in report["changes"]],
                         ["/", "/10", "/2", "/A", "/a", "/a~1b", "/a~0b", "/\u00e9"])
        self.assertIn(b"\\u00e9", diff.serialize_report(report))

    def test_positional_arrays_numeric_order_and_tail_subtrees(self):
        report = diff.compare_states({"x": list(range(12)), "z": [1, {"x": 2}]},
                                     {"x": list(range(1, 13)) + [{"tail": []}], "z": [1]})
        self.assertEqual([e["path"] for e in report["changes"]],
                         ["/x/" + str(i) for i in range(13)] + ["/z/1"])
        self.assertEqual(report["changes"][-2:], [entry("added", "/x/12", "missing", "object"),
                                                  entry("removed", "/z/1", "object", "missing")])
        self.assertEqual(diff.compare_states({"x": [[1, 2], [3, 4]]},
                                            {"x": [[3, 4], [1, 2]]})["change_count"], 4)

    def test_representational_differences_and_repeated_bytes(self):
        before = self.folder / "before.json"
        after = self.folder / "after.json"
        before.write_bytes(b'{"z":2,"a":"\\u00e9","x":[null,true,1.0]}\r\n')
        after.write_bytes('{\n "x": [null, true, 1e0], "a": "\u00e9", "z": 2\n}'.encode())
        args = ["compare", "--before", str(before), "--after", str(after)]
        outputs = [self.invoke(args) for _ in range(3)]
        self.assertTrue(all(r.returncode == 0 and r.stdout == outputs[0].stdout for r in outputs))
        args = self.pair_args({"z": 1, "a": 0}, {"z": 2, "a": 1})
        first = self.invoke(args)
        Path(args[2]).write_bytes(b'{ "a":0, "z":1 }')
        Path(args[4]).write_bytes(b'{ "a":1, "z":2 }')
        self.assertEqual(first.stdout, self.invoke(args).stdout)

    def test_depth_limit_in_unchanged_and_added_subtrees(self):
        root = {}
        cursor = root
        for _ in range(diff.MAX_DEPTH - 1):
            cursor["x"] = {}
            cursor = cursor["x"]
        self.assertEqual(diff.compare_states(root, root)["comparison"], "equal")
        cursor["x"] = []
        for before in (root, {}):
            with self.assertRaisesRegex(diff.DiffError, "comparison limit exceeded"):
                diff.compare_states(before, root)
        self.assert_failure(self.invoke(self.pair_args(root, root)), "comparison limit exceeded")

    def test_extreme_decoder_recursion_is_categorical(self):
        bad = self.folder / "PRIVATE.json"
        bad.write_bytes(b'{"x":' + b'[' * 2000 + b'0' + b']' * 2000 + b'}')
        good = self.write("good.json", {})
        self.assert_failure(self.invoke(["compare", "--before", str(bad), "--after", good]),
                            "comparison limit exceeded")

    def test_node_limit_real_boundary(self):
        # Root object + array + scalars + second object root = 1,000,000.
        before = {"x": [None] * (diff.MAX_NODES - 3)}
        self.assertEqual(diff.inspect_inputs([(before, "before"), ({}, "after")]), set())
        before["x"].append(None)
        with self.assertRaisesRegex(diff.DiffError, "comparison limit exceeded"):
            diff.compare_states(before, {})
        self.assert_failure(self.invoke(self.pair_args(before, {})), "comparison limit exceeded")

    def test_record_metadata_is_bounded_even_when_ignored(self):
        record = {"schema_version": 1, "before": {}, "after": {}, "extra": [None] * diff.MAX_NODES}
        self.assert_failure(self.invoke(["compare", "--record", self.write("r.json", record)]),
                            "comparison limit exceeded")

    def test_change_limit_real_boundary(self):
        before = {"x": [0] * diff.MAX_CHANGES}
        after = {"x": [1] * diff.MAX_CHANGES}
        self.assertEqual(diff.compare_states(before, after)["change_count"], diff.MAX_CHANGES)
        before["x"].append(0)
        after["x"].append(1)
        self.assert_failure(self.invoke(self.pair_args(before, after)), "comparison limit exceeded")

    def test_sensitive_policy_and_recursive_collection(self):
        for key in ("user_key", "accessToken", "AUTHORIZATION", "proxy-Authorization", "cookie",
                    "cookies", "Set-Cookie", "signature", "data_hash", "password", "secret",
                    "token", "session_id", "api_key"):
            with self.subTest(key=key):
                before = {key: {"nested": ["PRIVATE-credential", "", 1]}, "x/PRIVATE-credential~": 0}
                after = {key: {"nested": ["PRIVATE-credential", "", 1]}, "x/PRIVATE-credential~": 1}
                result = self.invoke(self.pair_args(before, after))
                self.assertEqual(result.returncode, 1)
                self.assertNotIn(b"PRIVATE-credential", result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout)["changes"][0]["path"], "/x~1[REDACTED]~0")
        self.assertEqual(diff.inspect_inputs([({"secret": {"not-collected-key": ["a", "b"]}}, "before")]),
                         {"a", "b"})

    def test_collects_both_states_and_complete_record(self):
        record = {"schema_version": 1, "before": {"left-secret": 0, "right-secret": 0,
                  "meta-secret": 0, "token": "left-secret"}, "after": {"left-secret": 1,
                  "right-secret": 1, "meta-secret": 1, "token": "right-secret"},
                  "extra": {"authorization": "meta-secret"}}
        # Distinct prefixes avoid collapsing the three secret-bearing paths.
        for state in (record["before"], record["after"]):
            for index, key in enumerate(("left-secret", "right-secret", "meta-secret")):
                state[str(index) + key] = state.pop(key)
        result = self.invoke(["compare", "--record", self.write("r.json", record)])
        self.assertEqual(result.returncode, 1)
        for secret in (b"left-secret", b"right-secret", b"meta-secret"):
            self.assertNotIn(secret, result.stdout + result.stderr)

    def test_sensitive_path_collisions_never_merge_changes(self):
        for before, after in (({"token": ["PRIVATE-a", "PRIVATE-b"]},
                               {"token": ["PRIVATE-a", "PRIVATE-b"], "PRIVATE-a": 0, "PRIVATE-b": 1}),
                              ({"token": "PRIVATE-a"}, {"token": "PRIVATE-a", "PRIVATE-a": 1, "[REDACTED]": 2})):
            self.assert_failure(self.invoke(self.pair_args(before, after)), "comparison path ambiguity")

    def test_overlapping_secrets_and_repeated_occurrences(self):
        before = {"token": ["PRIVATE-long", "PRIVATE"], "xPRIVATE-longPRIVATE": 0}
        after = {"token": ["PRIVATE-long", "PRIVATE"], "xPRIVATE-longPRIVATE": 1}
        result = self.invoke(self.pair_args(before, after))
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(b"PRIVATE", result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["changes"][0]["path"], "/x[REDACTED][REDACTED]")

    def test_serialization_and_memory_failures_have_no_report(self):
        args = self.pair_args({}, {})
        for target, error, category in (("json.dumps", ValueError("PRIVATE"), "report serialization failed"),
                                        ("report_from_arguments", MemoryError("PRIVATE"), "comparison limit exceeded")):
            output, diagnostic = io.BytesIO(), io.StringIO()
            with patch("state_diff." + target, side_effect=error):
                self.assertEqual(diff.main(args, output, diagnostic), 2)
            self.assertEqual(output.getvalue(), b"")
            self.assertEqual(diagnostic.getvalue(), category + "\n")

    def test_output_failure_and_short_write_are_categorical(self):
        class Broken:
            def write(self, data):
                raise BrokenPipeError("PRIVATE-path")
        class Short:
            def write(self, data):
                return 0
        class BrokenFlush:
            def write(self, data):
                return len(data)
            def flush(self):
                raise OSError("PRIVATE-path")
        for sink in (Broken(), Short(), BrokenFlush()):
            diagnostic = io.StringIO()
            self.assertEqual(diff.main(self.pair_args({}, {}), sink, diagnostic), 2)
            self.assertEqual(diagnostic.getvalue(), "output failed\n")
        self.assertEqual(diff.main(self.pair_args({}, {}), Broken(), Broken()), 2)

    def test_containment_full_disposable_tree_success_and_failure(self):
        work = self.folder / "checkout"
        (work / "tools/state-diff").mkdir(parents=True)
        copied = work / "tools/state-diff/state_diff.py"
        copied.write_bytes(TOOL.read_bytes())
        (work / "saves").mkdir()
        (work / "saves/PRIVATE-player.json").write_bytes(b"opaque runtime save")
        (work / "tests/saves").mkdir(parents=True)
        for path in (PRE, POST):
            (work / "tests/saves" / path.name).write_bytes(path.read_bytes())
        (work / "server.py").write_text("raise RuntimeError('must not import')", encoding="utf-8")
        (work / "archive.swf").write_bytes(b"preserved Flash archive")
        (self.folder / "surrounding-marker").write_bytes(b"untouched")
        bad = work / "bad.json"
        bad.write_bytes(b'{"PRIVATE": NaN}')
        record = work / "record.json"
        record.write_text('{"schema_version":1,"before":{},"after":{"x":1}}', encoding="utf-8")
        original = snapshot(self.folder)
        cases = [(["compare", "--before", str(work / "tests/saves" / PRE.name),
                   "--after", str(work / "tests/saves" / POST.name)], 1),
                 (["compare", "--record", str(record)], 1),
                 (["compare", "--before", str(bad), "--after", str(record)], 2),
                 (["compare"], 2)]
        for args, status in cases:
            result = subprocess.run([sys.executable, "-B", str(copied)] + args,
                                    cwd=str(work), capture_output=True, timeout=30)
            self.assertEqual(result.returncode, status)
            self.assertEqual(snapshot(self.folder), original)

    def test_no_runtime_network_process_or_hidden_discovery(self):
        args = self.pair_args({"unknown": 1}, {"unknown": 2})
        bad = self.folder / "PRIVATE-invalid.json"
        bad.write_bytes(b'{"PRIVATE":NaN}')
        record = self.write("record.json", {"schema_version": 1, "before": {}, "after": {}})
        output, diagnostic = io.BytesIO(), io.StringIO()
        # Audit actual reads/imports/side effects, not merely source spellings.
        events = []
        active = [True]
        def audit(event, values):
            if not active[0]:
                return
            if event == "open":
                name, mode, flags = values
                events.append(Path(name).resolve())
                if mode not in (None, "r", "rb") or flags & 3:
                    raise AssertionError("unexpected write")
            if event.startswith(("socket.", "subprocess.", "os.system", "os.mkdir", "os.remove", "os.rename")):
                raise AssertionError("unexpected side effect")
            if event == "import" and values[0].split(".")[0] in {
                    "server", "sessions", "engine", "command", "legacy_command_recorder", "webbrowser"}:
                raise AssertionError("unexpected runtime import")
        sys.addaudithook(audit)
        try:
            with patch.object(Path, "glob", side_effect=AssertionError("hidden discovery")), \
                 patch.object(Path, "rglob", side_effect=AssertionError("hidden discovery")):
                self.assertEqual(diff.main(args, output, diagnostic), 1)
                self.assertEqual(diff.main(["compare", "--record", record], io.BytesIO(), io.StringIO()), 0)
                self.assertEqual(diff.main(["compare", "--before", str(bad), "--after", args[4]],
                                           io.BytesIO(), io.StringIO()), 2)
        finally:
            active[0] = False
        self.assertEqual(set(events), {Path(args[2]).resolve(), Path(args[4]).resolve(),
                                      bad.resolve(), Path(record).resolve()})
        self.assertEqual(diagnostic.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
