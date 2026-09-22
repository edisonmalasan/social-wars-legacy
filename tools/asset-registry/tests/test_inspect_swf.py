import contextlib
import hashlib
import io
import json
import re
import struct
import sys
from pathlib import Path
import shutil
import tempfile
import unittest
import zlib
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "asset-registry"))

import inspect_swf as inspector


def tag(code, payload):
    """Encode one SWF tag with a short or long length header."""
    if len(payload) < 0x3F:
        return struct.pack("<H", (code << 6) | len(payload)) + payload
    return (struct.pack("<H", (code << 6) | 0x3F)
            + struct.pack("<I", len(payload)) + payload)


def rect_bytes(xmax_twips, ymax_twips):
    """Minimal FrameSize RECT covering (0,0)-(xmax,ymax) twips."""
    nbits = max(xmax_twips.bit_length(), ymax_twips.bit_length(), 1)
    value = 0
    width = 5 + 4 * nbits
    value |= 0 << (width - 5)  # placeholder, rebuilt below
    bits = []
    for field in (0, xmax_twips, 0, ymax_twips):
        bits.append(format(field, "0%db" % nbits))
    stream = format(nbits, "05b") + "".join(bits)
    stream += "0" * ((-len(stream)) % 8)
    return int(stream, 2).to_bytes(len(stream) // 8, "big")


def symbol_payload(names):
    payload = struct.pack("<H", len(names))
    for index, name in enumerate(names, start=1):
        payload += struct.pack("<H", index) + name.encode("utf-8") + b"\x00"
    return payload


def make_swf(version=10, rate=24.0, frames=2, tags=(), compressed=True):
    body = rect_bytes(550 * 20, 400 * 20)
    body += struct.pack("<H", int(rate * 256)) + struct.pack("<H", frames)
    body += b"".join(tags)
    if compressed:
        return b"CWS" + bytes([version]) + struct.pack("<I", 8 + len(body)) \
            + zlib.compress(body)
    return b"FWS" + bytes([version]) + struct.pack("<I", 8 + len(body)) + body


def sample_tags():
    """Shape + sprite + sound + labels + ABC + End, mirroring real files."""
    sprite_inner = (tag(26, b"\x01\x00") + tag(43, b"idle\x00")
                    + tag(1, b"") + tag(0, b""))
    return [
        tag(9, b"\xff\xff\xff"),
        tag(20, struct.pack("<H", 7) + b"\x05\x03\x02\x01\x00" + b"\x00" * 8),
        tag(14, struct.pack("<H", 9) + bytes([0x2C]) + b"\x00" * 4),
        tag(76, symbol_payload(["house_main"])),
        tag(86, b"\x01\x00Scene 1\x00\x01\x00idle\x00"),
        tag(82, b"\x00" * 6),
        tag(39, struct.pack("<HH", 5, 2) + sprite_inner),
        tag(1, b""),
        tag(1, b""),
        tag(0, b""),
    ]


def snapshot(root):
    return {str(path.relative_to(root)).replace("\\", "/"):
            ("directory" if path.is_dir() else path.read_bytes())
            for path in Path(root).rglob("*")}


def run_main(argv):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = inspector.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def make_fixture_tree(swf_files):
    """Synthetic repo root: N SWF files plus a matching registry.json."""
    temporary = tempfile.TemporaryDirectory()
    work = Path(temporary.name) / "repo"
    entries = []
    for name, payload in swf_files.items():
        target = work / "assets" / "sprites" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        entries.append({
            "path": "assets/sprites/" + name,
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "extension": ".swf",
            "directory_class": "assets",
            "status": "registered",
        })
    registry = {
        "schema_version": 1,
        "policy": "asset-registry-v1",
        "result": "success",
        "inputs": {},
        "counts": {"files": len(entries)},
        "entries": sorted(entries, key=lambda entry: entry["path"]),
    }
    tools = work / "tools" / "asset-registry"
    (tools / "schemas").mkdir(parents=True)
    for name in ("inspection.schema.json", "inspection_entry.schema.json"):
        shutil.copy2(ROOT / "tools" / "asset-registry" / "schemas" / name,
                     tools / "schemas" / name)
    (tools / "registry.json").write_text(json.dumps(registry), encoding="utf-8")
    return temporary, work


def read_out_json(out, relative):
    return json.loads((out / relative).read_text(encoding="utf-8"))


_REAL_INSPECTION = None


def real_inspection():
    """One shared real-corpus inspection writing to a temp out-root."""
    global _REAL_INSPECTION
    if _REAL_INSPECTION is None:
        temporary = tempfile.TemporaryDirectory()
        out = Path(temporary.name) / "out"
        out.mkdir(parents=True)
        code, stdout, _ = run_main(["--repo-root", str(ROOT),
                                    "--out-root", str(out)])
        assert code == 0, stdout
        _REAL_INSPECTION = (temporary, out)
    return _REAL_INSPECTION[1]


class SyntheticParseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary, cls.work = make_fixture_tree({
            "flat.swf": make_swf(tags=sample_tags()),
            "plain.swf": make_swf(compressed=False, tags=[tag(1, b""), tag(0, b"")]),
        })
        cls.addClassCleanup(cls.temporary.cleanup)
        code, stdout, _ = run_main(["--repo-root", str(cls.work),
                                    "--out-root", str(cls.work)])
        assert code == 0, stdout
        cls.document = read_out_json(cls.work, "tools/asset-registry/inspection.json")

    def test_header_fields(self):
        entry = self.document["entries"]["assets/sprites/flat.swf"]
        self.assertEqual(entry["signature"], "CWS")
        self.assertEqual(entry["version"], 10)
        self.assertEqual(entry["frame_width"], 550)
        self.assertEqual(entry["frame_height"], 400)
        self.assertEqual(entry["frame_rate"], 24.0)
        self.assertEqual(entry["frame_count"], 2)
        self.assertEqual(entry["actual_length"],
                         len(make_swf(tags=sample_tags())))

    def test_tag_inventory_merges_nested_sprites(self):
        entry = self.document["entries"]["assets/sprites/flat.swf"]
        self.assertEqual(entry["tags"]["1"], 3)
        self.assertEqual(entry["tags"]["39"], 1)
        self.assertEqual(entry["tags"]["26"], 1)
        self.assertEqual(entry["tags"]["0"], 2)
        self.assertEqual(entry["sprite_count"], 1)
        self.assertEqual(entry["max_sprite_depth"], 1)

    def test_symbols_exports_bitmaps_sounds_labels(self):
        entry = self.document["entries"]["assets/sprites/flat.swf"]
        self.assertEqual(entry["symbols"], ["house_main"])
        self.assertEqual(entry["exports"], [])
        self.assertEqual(entry["bitmap_ids"], [7])
        self.assertEqual(entry["sound_ids"], [9])
        self.assertTrue(entry["has_abc"])
        self.assertFalse(entry["has_action"])
        self.assertEqual(entry["abc_count"], 1)
        self.assertEqual(entry["frame_labels"], ["idle", "idle"])
        self.assertEqual(entry["scene_count"], 1)

    def test_uncompressed_variant(self):
        entry = self.document["entries"]["assets/sprites/plain.swf"]
        self.assertEqual(entry["signature"], "FWS")
        self.assertEqual(entry["frame_count"], 2)
        self.assertFalse(entry["has_abc"])

    def test_counts(self):
        counts = self.document["counts"]
        self.assertEqual(counts["files"], 2)
        self.assertEqual(counts["with_abc"], 1)
        self.assertEqual(counts["bitmap_ids_total"], 1)
        self.assertEqual(counts["sound_ids_total"], 1)


class SyntheticFailureTests(unittest.TestCase):
    def build(self, files):
        temporary, work = make_fixture_tree(files)
        self.addCleanup(temporary.cleanup)
        return run_main(["--repo-root", str(work), "--out-root", str(work)])

    def test_truncated_body_exit_1(self):
        payload = make_swf(tags=sample_tags())[:-4]
        code, stdout, _ = self.build({"cut.swf": payload})
        self.assertEqual(code, 1)
        self.assertIn("cut.swf", " ".join(json.loads(stdout)["problems"]))

    def test_missing_end_exit_1(self):
        payload = make_swf(tags=[tag(1, b"")])
        code, stdout, _ = self.build({"noend.swf": payload})
        self.assertEqual(code, 1)
        self.assertIn("End", " ".join(json.loads(stdout)["problems"]))

    def test_bad_signature_exit_1(self):
        payload = b"XXS" + make_swf(tags=sample_tags())[3:]
        code, stdout, _ = self.build({"bad.swf": payload})
        self.assertEqual(code, 1)
        self.assertIn("signature", " ".join(json.loads(stdout)["problems"]))

    def test_lzma_signature_refused(self):
        payload = b"ZWS" + make_swf(tags=sample_tags())[3:]
        code, stdout, _ = self.build({"lzma.swf": payload})
        self.assertEqual(code, 1)
        self.assertIn("LZMA", " ".join(json.loads(stdout)["problems"]))

    def test_missing_registry_exit_2(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        work = Path(temporary.name) / "repo"
        work.mkdir()
        code, _, stderr = run_main(["--repo-root", str(work),
                                    "--out-root", str(work)])
        self.assertEqual(code, 2)
        self.assertIn("registry", stderr)

    def test_failure_writes_nothing(self):
        temporary, work = make_fixture_tree(
            {"cut.swf": make_swf(tags=sample_tags())[:-4]})
        self.addCleanup(temporary.cleanup)
        code, _, _ = run_main(["--repo-root", str(work),
                               "--out-root", str(work)])
        self.assertEqual(code, 1)
        self.assertFalse((work / "tools" / "asset-registry"
                          / "inspection.json").exists())


class RealCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = real_inspection()
        cls.document = read_out_json(cls.out, "tools/asset-registry/inspection.json")

    def test_corpus_counts_match_measurements(self):
        counts = self.document["counts"]
        self.assertEqual(counts["files"], 1176)
        self.assertEqual(counts["versions"], {"10": 659, "11": 377,
                                              "15": 124, "17": 16})
        self.assertEqual(counts["with_abc"], 1175)
        self.assertEqual(counts["with_action"], 0)

    def test_sample_file_matches_probed_values(self):
        entry = self.document["entries"]["assets/sprites/0001_house_1_m.swf"]
        self.assertEqual(entry["signature"], "CWS")
        self.assertEqual(entry["version"], 10)
        self.assertEqual(entry["frame_rate"], 24.0)
        self.assertEqual(entry["frame_count"], 1)
        self.assertEqual(entry["symbols"], ["0001_house_1_m"])
        self.assertGreater(entry["sprite_count"], 0)

    def test_every_entry_terminated_and_typed(self):
        for path, entry in self.document["entries"].items():
            self.assertTrue(path.endswith(".swf"), path)
            self.assertGreater(entry["frame_count"], 0, path)
            self.assertIn("0", entry["tags"], path)
            self.assertIs(type(entry["frame_width"]), int)
            self.assertIsInstance(entry["frame_labels"], list)

    def test_registry_fingerprint_recorded(self):
        registry = json.loads(
            (ROOT / "tools" / "asset-registry" / "registry.json").read_text(
                encoding="utf-8"))
        expected = hashlib.sha256(
            json.dumps(registry["entries"], sort_keys=True).encode("utf-8")
        ).hexdigest()
        self.assertEqual(self.document["inputs"]["registry_fingerprint"], expected)
        self.assertEqual(self.document["inputs"]["registry_files"], 3215)

    def test_repeated_runs_byte_identical(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        out = Path(temporary.name) / "out"
        out.mkdir()
        code, _, _ = run_main(["--repo-root", str(ROOT), "--out-root", str(out)])
        self.assertEqual(code, 0)
        first = (self.out / "tools" / "asset-registry"
                 / "inspection.json").read_bytes()
        second = (out / "tools" / "asset-registry"
                  / "inspection.json").read_bytes()
        self.assertEqual(first, second)


class TraceabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inspection_schema = json.loads(
            (ROOT / "tools" / "asset-registry" / "schemas"
             / "inspection.schema.json").read_text(encoding="utf-8"))
        cls.entry_schema = json.loads(
            (ROOT / "tools" / "asset-registry" / "schemas"
             / "inspection_entry.schema.json").read_text(encoding="utf-8"))
        out = real_inspection()
        document = read_out_json(out, "tools/asset-registry/inspection.json")
        cls.document = document
        cls.entry = document["entries"]["assets/sprites/0001_house_1_m.swf"]

    def test_every_required_field_is_enforced(self):
        for schema, item, label in (
                (self.inspection_schema, self.document, "inspection"),
                (self.entry_schema, self.entry, "inspection_entry")):
            for field in schema["required"]:
                mutated = dict(item)
                del mutated[field]
                problems = inspector.validate_against_schema(
                    mutated, schema, label)
                self.assertTrue(
                    any("missing required field" in problem
                        and field in problem for problem in problems),
                    "no validator check for required field %s.%s"
                    % (label, field))

    def test_wrong_types_are_rejected(self):
        mutated = dict(self.entry)
        mutated["version"] = "10"
        self.assertTrue(inspector.validate_against_schema(
            mutated, self.entry_schema, "inspection_entry"))
        mutated = dict(self.entry)
        mutated["signature"] = "ZWS"
        problems = inspector.validate_against_schema(
            mutated, self.entry_schema, "inspection_entry")
        self.assertTrue(any("enum mismatch" in problem for problem in problems))
        mutated = dict(self.entry)
        mutated["has_abc"] = 1
        self.assertTrue(inspector.validate_against_schema(
            mutated, self.entry_schema, "inspection_entry"))

    def test_kind_const_and_no_extra_properties(self):
        mutated = dict(self.document)
        mutated["policy"] = "asset-registry-v1"
        self.assertTrue(inspector.validate_against_schema(
            mutated, self.inspection_schema, "inspection"))
        mutated = dict(self.entry)
        mutated["invented_field"] = 1
        problems = inspector.validate_against_schema(
            mutated, self.entry_schema, "inspection_entry")
        self.assertTrue(any("additional property" in problem
                            for problem in problems))


class ContainmentTests(unittest.TestCase):
    def guarded_run(self, work, argv):
        opened = []
        real_io_open = io.open
        real_builtins_open = open

        def guarded_open(file, mode="r", *args, **kwargs):
            if any(flag in str(mode) for flag in ("w", "a", "x", "+")):
                opened.append(("write", str(file)))
                return (real_builtins_open if guarded_open.is_builtin
                        else real_io_open)(file, mode, *args, **kwargs)
            opened.append(("read", str(file)))
            return (real_builtins_open if guarded_open.is_builtin
                    else real_io_open)(file, mode, *args, **kwargs)

        def io_guard(file, mode="r", *args, **kwargs):
            guarded_open.is_builtin = False
            return guarded_open(file, mode, *args, **kwargs)

        def builtins_guard(file, mode="r", *args, **kwargs):
            guarded_open.is_builtin = True
            return guarded_open(file, mode, *args, **kwargs)

        before = snapshot(work)
        with mock.patch("io.open", io_guard), \
                mock.patch("builtins.open", builtins_guard):
            code, stdout, stderr = run_main(argv)
        return code, stdout, stderr, opened, before

    def observed_sets(self, work, opened):
        reads = set()
        writes = set()
        for kind, raw in opened:
            try:
                relative = str(Path(raw).relative_to(work)).replace("\\", "/")
            except ValueError:
                self.fail("tool touched outside repo root: %r" % (raw,))
            if kind == "read":
                reads.add(relative)
            else:
                writes.add(relative)
        return reads, writes

    def test_fixture_reads_exact_and_inputs_unchanged(self):
        temporary, work = make_fixture_tree({
            "flat.swf": make_swf(tags=sample_tags()),
        })
        try:
            code, _, _, opened, before = self.guarded_run(
                work, ["--repo-root", str(work), "--out-root", str(work)])
            self.assertEqual(code, 0)
            reads, writes = self.observed_sets(work, opened)
            self.assertEqual(writes, {"tools/asset-registry/inspection.json"})
            self.assertEqual(reads, {
                "assets/sprites/flat.swf",
                "tools/asset-registry/registry.json",
                "tools/asset-registry/schemas/inspection.schema.json",
                "tools/asset-registry/schemas/inspection_entry.schema.json",
            })
            after = snapshot(work)
            new_files = {path for path in set(after) - set(before)
                         if after[path] != "directory"}
            self.assertEqual(new_files, {"tools/asset-registry/inspection.json"})
            for path, payload in before.items():
                if path == "tools/asset-registry/inspection.json":
                    continue
                self.assertEqual(after[path], payload, path)
        finally:
            temporary.cleanup()

    def test_no_forbidden_imports_or_execution(self):
        source = (ROOT / "tools" / "asset-registry"
                  / "inspect_swf.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            match = re.match(r"\s*(import|from)\s+(\S+)", line)
            if not match:
                continue
            module = match.group(2).split(".")[0]
            self.assertNotIn(module, ("get_game_config", "jsonpatch", "flask",
                                      "server", "command", "engine",
                                      "requests", "subprocess", "socket",
                                      "urllib", "webbrowser", "http",
                                      "shutil", "lzma"),
                             "forbidden import: " + line)
        self.assertNotIn("Popen", source)
        self.assertNotIn("os.system", source)
        self.assertNotIn("exec(", source)
        self.assertNotIn("eval(", source)


if __name__ == "__main__":
    unittest.main()
