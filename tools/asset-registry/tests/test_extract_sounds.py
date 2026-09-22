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

import extract_sounds as extractor


def tag(code, payload):
    if len(payload) < 0x3F:
        return struct.pack("<H", (code << 6) | len(payload)) + payload
    return (struct.pack("<H", (code << 6) | 0x3F)
            + struct.pack("<I", len(payload)) + payload)


def rect_bytes(xmax_twips, ymax_twips):
    nbits = max(xmax_twips.bit_length(), ymax_twips.bit_length(), 1)
    bits = []
    for field in (0, xmax_twips, 0, ymax_twips):
        bits.append(format(field, "0%db" % nbits))
    stream = format(nbits, "05b") + "".join(bits)
    stream += "0" * ((-len(stream)) % 8)
    return int(stream, 2).to_bytes(len(stream) // 8, "big")


def sound_tag(character_id, format_nibble, frames, rate=3, size=1,
              sound_type=1, prefix=b"\x00" * 6):
    """DefineSound tag: id + characteristics + header bytes + MP3 frames."""
    flags = (format_nibble << 4) | (rate << 2) | (size << 1) | sound_type
    return tag(14, struct.pack("<H", character_id) + bytes([flags])
               + prefix + frames)


MP3_FRAME = b"\xff\xfb\x90\x00" + b"\x00" * 100


def make_swf(sound_tags, compressed=True):
    body = rect_bytes(100 * 20, 100 * 20)
    body += struct.pack("<H", int(24.0 * 256)) + struct.pack("<H", 1)
    body += b"".join(sound_tags) + tag(0, b"")
    if compressed:
        return b"CWS" + bytes([10]) + struct.pack("<I", 8 + len(body)) \
            + zlib.compress(body)
    return b"FWS" + bytes([10]) + struct.pack("<I", 8 + len(body)) + body


def snapshot(root):
    return {str(path.relative_to(root)).replace("\\", "/"):
            ("directory" if path.is_dir() else path.read_bytes())
            for path in Path(root).rglob("*")}


def run_main(argv):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = extractor.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def make_fixture_tree(swf_files):
    """Synthetic repo root with registry+inspection entries for N SWFs."""
    temporary = tempfile.TemporaryDirectory()
    work = Path(temporary.name) / "repo"
    entries = {}
    registry_entries = []
    for name, payload in swf_files.items():
        relative = "assets/swf/" + name
        target = work / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        registry_entries.append({
            "path": relative,
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "extension": ".swf",
            "directory_class": "assets",
            "status": "registered",
        })
        entries[relative] = {"sound_ids": [1]}
    tools = work / "tools" / "asset-registry"
    (tools / "schemas").mkdir(parents=True)
    for name in ("extraction.schema.json", "extraction_sound.schema.json"):
        shutil.copy2(ROOT / "tools" / "asset-registry" / "schemas" / name,
                     tools / "schemas" / name)
    (tools / "registry.json").write_text(json.dumps({
        "schema_version": 1, "policy": "asset-registry-v1", "result": "success",
        "inputs": {}, "counts": {}, "entries": registry_entries,
    }), encoding="utf-8")
    (tools / "inspection.json").write_text(json.dumps({
        "schema_version": 1, "policy": "swf-inspection-v1", "result": "success",
        "inputs": {}, "counts": {}, "entries": entries,
    }), encoding="utf-8")
    return temporary, work


def read_out_json(out, relative):
    return json.loads((out / relative).read_text(encoding="utf-8"))


_REAL_EXTRACTION = None


def real_extraction():
    """One shared real-file extraction writing to a temp out-root."""
    global _REAL_EXTRACTION
    if _REAL_EXTRACTION is None:
        temporary = tempfile.TemporaryDirectory()
        out = Path(temporary.name) / "out"
        out.mkdir(parents=True)
        code, stdout, _ = run_main(["--repo-root", str(ROOT),
                                    "--out-root", str(out)])
        assert code == 0, stdout
        _REAL_EXTRACTION = (temporary, out)
    return _REAL_EXTRACTION[1]


class SyntheticExtractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary, cls.work = make_fixture_tree({
            "two.swf": make_swf([
                sound_tag(4, 2, MP3_FRAME),
                sound_tag(9, 2, MP3_FRAME + MP3_FRAME, rate=1, size=0,
                          sound_type=0),
            ]),
        })
        cls.addClassCleanup(cls.temporary.cleanup)
        code, stdout, _ = run_main(["--repo-root", str(cls.work),
                                    "--out-root", str(cls.work)])
        assert code == 0, stdout
        cls.document = read_out_json(cls.work, "tools/asset-registry/extraction.json")
        cls.statuses = read_out_json(cls.work, "tools/asset-registry/statuses.json")

    def test_two_sounds_sliced_from_sync(self):
        self.assertEqual(self.document["counts"]["sounds"], 2)
        by_id = {sound["character_id"]: sound
                 for sound in self.document["sounds"]}
        self.assertEqual(sorted(by_id), [4, 9])
        self.assertEqual(by_id[4]["sync_offset"], 9)
        self.assertEqual(by_id[4]["format"], 2)
        self.assertEqual(by_id[9]["rate"], 1)
        self.assertEqual(by_id[9]["size"], 0)
        self.assertEqual(by_id[9]["sound_type"], 0)
        for sound in by_id.values():
            data = (self.work / sound["output"]).read_bytes()
            self.assertEqual(len(data), sound["output_bytes"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), sound["sha256"])
            self.assertEqual(data[:2], b"\xff\xfb")

    def test_status_overlay(self):
        self.assertEqual(self.statuses["statuses"],
                         {"assets/swf/two.swf": "extracted"})
        self.assertEqual(self.statuses["policy"], "asset-statuses-v1")


class SyntheticFailureTests(unittest.TestCase):
    def build(self, files):
        temporary, work = make_fixture_tree(files)
        self.addCleanup(temporary.cleanup)
        return run_main(["--repo-root", str(work), "--out-root", str(work)])

    def test_non_mp3_format_exit_1(self):
        code, stdout, _ = self.build({
            "adpcm.swf": make_swf([sound_tag(1, 1, b"\x00" * 50)]),
        })
        self.assertEqual(code, 1)
        self.assertIn("non-MP3", " ".join(json.loads(stdout)["problems"]))

    def test_shifted_sync_exit_1(self):
        code, stdout, _ = self.build({
            "shift.swf": make_swf([sound_tag(1, 2, MP3_FRAME,
                                             prefix=b"\x00" * 7)]),
        })
        self.assertEqual(code, 1)
        self.assertIn("sync drift", " ".join(json.loads(stdout)["problems"]))

    def test_missing_sync_exit_1(self):
        code, stdout, _ = self.build({
            "nosync.swf": make_swf([sound_tag(1, 2, b"\x00" * 50)]),
        })
        self.assertEqual(code, 1)
        self.assertIn("frame sync", " ".join(json.loads(stdout)["problems"]))

    def test_truncated_swf_exit_1(self):
        payload = make_swf([sound_tag(1, 2, MP3_FRAME)])[:-10]
        code, stdout, _ = self.build({"cut.swf": payload})
        self.assertEqual(code, 1)

    def test_missing_inspection_exit_2(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        work = Path(temporary.name) / "repo"
        work.mkdir()
        code, _, stderr = run_main(["--repo-root", str(work),
                                    "--out-root", str(work)])
        self.assertEqual(code, 2)
        self.assertIn("inspection", stderr)

    def test_failure_writes_nothing(self):
        temporary, work = make_fixture_tree({
            "adpcm.swf": make_swf([sound_tag(1, 1, b"\x00" * 50)]),
        })
        self.addCleanup(temporary.cleanup)
        code, _, _ = run_main(["--repo-root", str(work),
                               "--out-root", str(work)])
        self.assertEqual(code, 1)
        self.assertFalse((work / "assets" / "converted").exists())
        self.assertFalse((work / "tools" / "asset-registry"
                          / "extraction.json").exists())
        self.assertFalse((work / "tools" / "asset-registry"
                          / "statuses.json").exists())


class RealFileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = real_extraction()
        cls.document = read_out_json(cls.out, "tools/asset-registry/extraction.json")
        cls.statuses = read_out_json(cls.out, "tools/asset-registry/statuses.json")

    def test_twenty_seven_sounds_ids_ordered(self):
        self.assertEqual(self.document["counts"]["sounds"], 27)
        self.assertEqual([sound["character_id"] for sound in self.document["sounds"]],
                         list(range(1, 28)))

    def test_sync_offsets_uniform_nine(self):
        for sound in self.document["sounds"]:
            self.assertEqual(sound["sync_offset"], 9)
            self.assertEqual(sound["format"], 2)

    def test_outputs_match_digests(self):
        for sound in self.document["sounds"]:
            data = (self.out / sound["output"]).read_bytes()
            self.assertEqual(len(data), sound["output_bytes"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), sound["sha256"])
            self.assertEqual(data[0], 0xFF)
            self.assertTrue(data[1] & 0xE0 == 0xE0)

    def test_status_overlay_single_file(self):
        self.assertEqual(self.statuses["statuses"],
                         {"assets/swf/dynamic2.swf": "extracted"})

    def test_repeated_runs_byte_identical(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        out = Path(temporary.name) / "out"
        out.mkdir()
        code, _, _ = run_main(["--repo-root", str(ROOT), "--out-root", str(out)])
        self.assertEqual(code, 0)
        for name in ("tools/asset-registry/extraction.json",
                     "tools/asset-registry/statuses.json"):
            self.assertEqual((self.out / name).read_bytes(),
                             (out / name).read_bytes(), name)
        for sound in self.document["sounds"]:
            self.assertEqual((self.out / sound["output"]).read_bytes(),
                             (out / sound["output"]).read_bytes(),
                             sound["output"])


class TraceabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.extraction_schema = json.loads(
            (ROOT / "tools" / "asset-registry" / "schemas"
             / "extraction.schema.json").read_text(encoding="utf-8"))
        cls.sound_schema = json.loads(
            (ROOT / "tools" / "asset-registry" / "schemas"
             / "extraction_sound.schema.json").read_text(encoding="utf-8"))
        out = real_extraction()
        cls.document = read_out_json(out, "tools/asset-registry/extraction.json")
        cls.sound = cls.document["sounds"][0]

    def test_every_required_field_is_enforced(self):
        for schema, item, label in (
                (self.extraction_schema, self.document, "extraction"),
                (self.sound_schema, self.sound, "sound")):
            for field in schema["required"]:
                mutated = dict(item)
                del mutated[field]
                problems = extractor.validate_against_schema(
                    mutated, schema, label)
                self.assertTrue(
                    any("missing required field" in problem
                        and field in problem for problem in problems),
                    "no validator check for required field %s.%s"
                    % (label, field))

    def test_wrong_types_and_bounds_rejected(self):
        mutated = dict(self.sound)
        mutated["character_id"] = "1"
        self.assertTrue(extractor.validate_against_schema(
            mutated, self.sound_schema, "sound"))
        mutated = dict(self.sound)
        mutated["format"] = 1
        problems = extractor.validate_against_schema(
            mutated, self.sound_schema, "sound")
        self.assertTrue(any("above maximum" in problem or "below minimum" in problem
                            for problem in problems))
        mutated = dict(self.sound)
        mutated["rate"] = 9
        self.assertTrue(extractor.validate_against_schema(
            mutated, self.sound_schema, "sound"))

    def test_digest_format_enforced(self):
        problems = []
        extractor.validate_digest("xyz", "probe", problems)
        self.assertTrue(problems)


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

    def test_fixture_reads_exact_and_sources_unchanged(self):
        temporary, work = make_fixture_tree({
            "two.swf": make_swf([sound_tag(4, 2, MP3_FRAME)]),
        })
        try:
            code, _, _, opened, before = self.guarded_run(
                work, ["--repo-root", str(work), "--out-root", str(work)])
            self.assertEqual(code, 0)
            reads, writes = self.observed_sets(work, opened)
            self.assertEqual(writes, {
                "assets/converted/sounds/4.mp3",
                "tools/asset-registry/extraction.json",
                "tools/asset-registry/statuses.json",
            })
            self.assertEqual(reads, {
                "assets/swf/two.swf",
                "tools/asset-registry/inspection.json",
                "tools/asset-registry/schemas/extraction.schema.json",
                "tools/asset-registry/schemas/extraction_sound.schema.json",
            })
            after = snapshot(work)
            new_files = {path for path in set(after) - set(before)
                         if after[path] != "directory"}
            self.assertEqual(new_files, {
                "assets/converted/sounds/4.mp3",
                "tools/asset-registry/extraction.json",
                "tools/asset-registry/statuses.json",
            })
            for path, payload in before.items():
                self.assertEqual(after[path], payload, path)
        finally:
            temporary.cleanup()

    def test_no_forbidden_imports_or_decoding(self):
        source = (ROOT / "tools" / "asset-registry"
                  / "extract_sounds.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            match = re.match(r"\s*(import|from)\s+(\S+)", line)
            if not match:
                continue
            module = match.group(2).split(".")[0]
            self.assertNotIn(module, ("get_game_config", "jsonpatch", "flask",
                                      "server", "command", "engine",
                                      "requests", "subprocess", "socket",
                                      "urllib", "webbrowser", "http",
                                      "shutil", "wave", "audioop", "aifc",
                                      "mutagen", "pydub"),
                             "forbidden import: " + line)
        self.assertNotIn("Popen", source)
        self.assertNotIn("os.system", source)


if __name__ == "__main__":
    unittest.main()
