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

import extract_images as extractor


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


def make_swf(tags, compressed=True, version=10):
    body = rect_bytes(100 * 20, 100 * 20)
    body += struct.pack("<H", int(24.0 * 256)) + struct.pack("<H", 1)
    body += b"".join(tags) + tag(0, b"")
    if compressed:
        return b"CWS" + bytes([version]) + struct.pack("<I", 8 + len(body)) \
            + zlib.compress(body)
    return b"FWS" + bytes([version]) + struct.pack("<I", 8 + len(body)) + body


TINY_JPEG = (b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01"
             b"\x00\x00\xff\xdb\x00\x43\x00" + b"\x08" * 64
             + b"\xff\xc0\x00\x0b\x08\x00\x02\x00\x03\x01\x11\x00\x02\x11\x01"
             + b"\x03\x11\x01\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00\xd2\xcf"
             + b"\xff\xd9")


def argb_pixels(quads, width, height):
    assert len(quads) == width * height
    assert all(len(quad) == 4 for quad in quads)
    return zlib.compress(b"".join(quads))


def colormap_payload(character_id, palette, indices, width, tag_code=36):
    entry_size = 4 if tag_code == 36 else 3
    stream = b"".join(palette) + bytes(indices)
    return (struct.pack("<H", character_id) + bytes([3])
            + struct.pack("<HH", width, len(indices) // width
                          if width else 0)
            + bytes([len(palette) - 1]) + zlib.compress(stream))


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
    """Synthetic repo root with inspection entries for N SWFs."""
    temporary = tempfile.TemporaryDirectory()
    work = Path(temporary.name) / "repo"
    entries = {}
    for name, payload in swf_files.items():
        relative = "assets/sprites/" + name
        target = work / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        entries[relative] = {"sound_ids": []}
    tools = work / "tools" / "asset-registry"
    (tools / "schemas").mkdir(parents=True)
    for name in ("bitmap_extraction.schema.json", "extracted_bitmap.schema.json"):
        shutil.copy2(ROOT / "tools" / "asset-registry" / "schemas" / name,
                     tools / "schemas" / name)
    (tools / "inspection.json").write_text(json.dumps({
        "schema_version": 1, "policy": "swf-inspection-v1", "result": "success",
        "inputs": {}, "counts": {}, "entries": entries,
    }), encoding="utf-8")
    return temporary, work


def read_out_json(out, relative):
    return json.loads((out / relative).read_text(encoding="utf-8"))


class SyntheticFamilyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.argb = [b"\xff\xff\x00\x00", b"\xff\x00\xff\x00",
                    b"\xff\x00\x00\xff", b"\x80\x11\x22\x33"]
        cls.palette = [b"\xff\xff\x00\x00", b"\xff\x00\xff\x00"]
        cls.temporary, cls.work = make_fixture_tree({
            "all.swf": make_swf([
                tag(6, struct.pack("<H", 11) + TINY_JPEG),
                tag(35, struct.pack("<H", 12) + struct.pack("<I", len(TINY_JPEG))
                    + TINY_JPEG
                    + zlib.compress(bytes([10, 20, 30, 40, 50, 60]))),
                tag(36, struct.pack("<H", 13) + bytes([5])
                    + struct.pack("<HH", 2, 2) + argb_pixels(cls.argb, 2, 2)),
                tag(36, colormap_payload(14, cls.palette, [0, 1, 1, 0, 0, 1], 3)),
            ]),
        })
        cls.addClassCleanup(cls.temporary.cleanup)
        code, stdout, _ = run_main(["--repo-root", str(cls.work),
                                    "--out-root", str(cls.work)])
        assert code == 0, stdout
        cls.document = read_out_json(
            cls.work, "tools/asset-registry/image_extraction.json")

    def test_counts_and_families(self):
        counts = self.document["counts"]
        self.assertEqual(counts["bitmaps"], 4)
        self.assertEqual(counts["families"], {"jpeg": 1, "jpeg3": 1,
                                              "lossless": 2})

    def test_jpeg_verbatim_with_dimensions(self):
        by_id = {bitmap["character_id"]: bitmap
                 for bitmap in self.document["bitmaps"]}
        entry = by_id[11]
        self.assertEqual(entry["family"], "jpeg")
        self.assertEqual((entry["width"], entry["height"]), (3, 2))
        data = (self.work / [o["file"] for o in entry["outputs"]][0]).read_bytes()
        self.assertTrue(data.startswith(b"\xff\xd8"))

    def test_jpeg3_splits_alpha(self):
        by_id = {bitmap["character_id"]: bitmap
                 for bitmap in self.document["bitmaps"]}
        entry = by_id[12]
        self.assertEqual(entry["family"], "jpeg3")
        self.assertEqual((entry["width"], entry["height"]), (3, 2))
        files = {output["file"]: output for output in entry["outputs"]}
        self.assertEqual(len(files), 2)
        alpha_path = [path for path in files if path.endswith("_alpha.png")][0]
        data = (self.work / alpha_path).read_bytes()
        width, height, color = extractor.parse_png_ihdr(data, "probe")
        self.assertEqual((width, height, color), (3, 2, 0))

    def test_lossless_argb_round_trip(self):
        by_id = {bitmap["character_id"]: bitmap
                 for bitmap in self.document["bitmaps"]}
        entry = by_id[13]
        self.assertEqual(entry["family"], "lossless")
        self.assertEqual(entry["format"], 5)
        data = (self.work / [o["file"] for o in entry["outputs"]][0]).read_bytes()
        width, height, color = extractor.parse_png_ihdr(data, "probe")
        self.assertEqual((width, height, color), (2, 2, 6))

    def test_colormap_expansion(self):
        by_id = {bitmap["character_id"]: bitmap
                 for bitmap in self.document["bitmaps"]}
        entry = by_id[14]
        self.assertEqual(entry["format"], 3)
        data = (self.work / [o["file"] for o in entry["outputs"]][0]).read_bytes()
        width, height, color = extractor.parse_png_ihdr(data, "probe")
        self.assertEqual((width, height, color), (3, 2, 6))

    def test_statuses_overlay(self):
        statuses = read_out_json(self.work, "tools/asset-registry/statuses.json")
        self.assertEqual(statuses["statuses"],
                         {"assets/sprites/all.swf": "extracted"})
        self.assertEqual(statuses["policy"], "asset-statuses-v1")


class SyntheticFailureTests(unittest.TestCase):
    def build(self, files):
        temporary, work = make_fixture_tree(files)
        self.addCleanup(temporary.cleanup)
        return run_main(["--repo-root", str(work), "--out-root", str(work)])

    def test_unknown_lossless_format_exit_1(self):
        payload = (struct.pack("<H", 7) + bytes([4])
                   + struct.pack("<HH", 1, 1) + zlib.compress(b"\x00" * 2))
        code, stdout, _ = self.build({"bad.swf": make_swf([tag(36, payload)])})
        self.assertEqual(code, 1)
        self.assertIn("unsupported lossless format",
                      " ".join(json.loads(stdout)["problems"]))

    def test_alpha_dimension_mismatch_exit_1(self):
        payload = (struct.pack("<H", 8) + struct.pack("<I", len(TINY_JPEG))
                   + TINY_JPEG + zlib.compress(bytes([1, 2, 3])))
        code, stdout, _ = self.build({"alpha.swf": make_swf([tag(35, payload)])})
        self.assertEqual(code, 1)
        self.assertIn("alpha dimension mismatch",
                      " ".join(json.loads(stdout)["problems"]))

    def test_jpeg_without_soi_or_tables_exit_1(self):
        payload = struct.pack("<H", 9) + b"\x00" * 20
        code, stdout, _ = self.build({"nosoi.swf": make_swf([tag(21, payload)])})
        self.assertEqual(code, 1)
        self.assertIn("SOI", " ".join(json.loads(stdout)["problems"]))

    def test_tables_splice_path(self):
        tables = b"\xff\xd8\xff\xe0" + b"\x00" * 10
        payload = struct.pack("<H", 10) + b"\xff\xd9"
        code, stdout, _ = self.build({"splice.swf": make_swf([
            tag(8, tables), tag(21, payload)])})
        # ff d9 alone has SOI? No: starts ffd9 (SOI+EOI, no SOF) -> SOF scan fails.
        self.assertEqual(code, 1)

    def test_truncated_swf_exit_1(self):
        payload = make_swf([tag(6, struct.pack("<H", 11) + TINY_JPEG)])[:-8]
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
            "bad.swf": make_swf([tag(36, struct.pack("<H", 7) + bytes([4])
                                         + struct.pack("<HH", 1, 1)
                                         + zlib.compress(b"\x00" * 2))]),
        })
        self.addCleanup(temporary.cleanup)
        code, _, _ = run_main(["--repo-root", str(work),
                               "--out-root", str(work)])
        self.assertEqual(code, 1)
        self.assertFalse((work / "assets" / "converted").exists())
        self.assertFalse((work / "tools" / "asset-registry"
                          / "image_extraction.json").exists())
        self.assertFalse((work / "tools" / "asset-registry"
                          / "statuses.json").exists())


class RealSpotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.out = Path(cls.temporary.name) / "spot"
        (cls.out / "assets" / "converted" / "images").mkdir(parents=True)
        (cls.out / "tools" / "asset-registry").mkdir(parents=True)

    def extract_single(self, relative):
        """Run the converter helpers against one real file (no full build)."""
        data = (ROOT / relative).read_bytes()
        body = extractor.decompress_body(data, "probe")
        tags = list(extractor.walk_bitmap_tags(body, "probe"))
        self.assertTrue(tags)
        return tags

    def test_house_jpeg3_with_alpha_dims(self):
        tags = self.extract_single("assets/sprites/0001_house_1_m.swf")
        kinds = [code for code, _ in tags]
        self.assertIn(35, kinds)
        for code, payload in tags:
            if code == 35:
                character_id, jpeg, width, height, alpha_png = \
                    extractor.convert_jpeg3(payload, "probe")
                self.assertGreater(width, 0)
                self.assertGreater(height, 0)
                self.assertTrue(jpeg.startswith(b"\xff\xd8"))
                parsed = extractor.parse_png_ihdr(alpha_png, "probe")
                self.assertEqual(parsed, (width, height, 0))

    def test_depot_lossless_png_reparse(self):
        tags = self.extract_single("assets/sprites/0004_depot_steel_1_m.swf")
        lossless = [(code, payload) for code, payload in tags
                    if code in (20, 36)]
        self.assertTrue(lossless)
        code, payload = lossless[0]
        _, _, width, height, png = extractor.convert_lossless(
            code, payload, "probe")
        self.assertEqual(extractor.parse_png_ihdr(png, "probe")[:2],
                         (width, height))

    def test_plain_jpeg_verbatim_without_splice(self):
        data = (ROOT / "assets" / "flash" / "Basesec_1.4.10.swf").read_bytes()
        body = extractor.decompress_body(data, "probe")
        tags = list(extractor.walk_bitmap_tags(body, "probe"))
        plain = [(code, payload) for code, payload in tags
                 if code in (6, 21)]
        self.assertTrue(plain)
        for code, payload in plain[:3]:
            _, stream, spliced, width, height = extractor.convert_jpeg(
                code, payload, None, "probe")
            self.assertFalse(spliced)
            self.assertTrue(stream.startswith(b"\xff\xd8"))
            self.assertGreater(width, 0)
            self.assertGreater(height, 0)


class TraceabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.extraction_schema = json.loads(
            (ROOT / "tools" / "asset-registry" / "schemas"
             / "bitmap_extraction.schema.json").read_text(encoding="utf-8"))
        cls.bitmap_schema = json.loads(
            (ROOT / "tools" / "asset-registry" / "schemas"
             / "extracted_bitmap.schema.json").read_text(encoding="utf-8"))
        temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        work = Path(temporary.name) / "repo"
        entries = {"assets/sprites/x.swf": {"sound_ids": []}}
        (work / "assets" / "sprites").mkdir(parents=True)
        payload = make_swf([tag(6, struct.pack("<H", 11) + TINY_JPEG)])
        (work / "assets" / "sprites" / "x.swf").write_bytes(payload)
        tools = work / "tools" / "asset-registry"
        (tools / "schemas").mkdir(parents=True)
        for name in ("bitmap_extraction.schema.json", "extracted_bitmap.schema.json"):
            shutil.copy2(ROOT / "tools" / "asset-registry" / "schemas" / name,
                         tools / "schemas" / name)
        (tools / "inspection.json").write_text(json.dumps({
            "schema_version": 1, "policy": "swf-inspection-v1", "result": "success",
            "inputs": {}, "counts": {}, "entries": entries,
        }), encoding="utf-8")
        code, stdout, _ = run_main(["--repo-root", str(work),
                                    "--out-root", str(work)])
        assert code == 0, stdout
        cls.document = read_out_json(work, "tools/asset-registry/image_extraction.json")
        cls.bitmap = cls.document["bitmaps"][0]

    def test_every_required_field_is_enforced(self):
        for schema, item, label in (
                (self.extraction_schema, self.document, "extraction"),
                (self.bitmap_schema, self.bitmap, "bitmap")):
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

    def test_wrong_types_are_rejected(self):
        mutated = dict(self.bitmap)
        mutated["character_id"] = "11"
        self.assertTrue(extractor.validate_against_schema(
            mutated, self.bitmap_schema, "bitmap"))
        mutated = dict(self.bitmap)
        mutated["family"] = "vector"
        problems = extractor.validate_against_schema(
            mutated, self.bitmap_schema, "bitmap")
        self.assertTrue(any("enum mismatch" in problem for problem in problems))
        mutated = dict(self.bitmap)
        mutated["width"] = -1
        self.assertTrue(extractor.validate_against_schema(
            mutated, self.bitmap_schema, "bitmap"))

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
            "one.swf": make_swf([tag(6, struct.pack("<H", 11) + TINY_JPEG)]),
        })
        try:
            code, _, _, opened, before = self.guarded_run(
                work, ["--repo-root", str(work), "--out-root", str(work)])
            self.assertEqual(code, 0)
            reads, writes = self.observed_sets(work, opened)
            self.assertEqual(writes, {
                "assets/converted/images/one/11.jpg",
                "tools/asset-registry/image_extraction.json",
                "tools/asset-registry/statuses.json",
            })
            self.assertEqual(reads, {
                "assets/sprites/one.swf",
                "tools/asset-registry/inspection.json",
                "tools/asset-registry/schemas/bitmap_extraction.schema.json",
                "tools/asset-registry/schemas/extracted_bitmap.schema.json",
            })
            after = snapshot(work)
            new_files = {path for path in set(after) - set(before)
                         if after[path] != "directory"}
            self.assertEqual(new_files, {
                "assets/converted/images/one/11.jpg",
                "tools/asset-registry/image_extraction.json",
                "tools/asset-registry/statuses.json",
            })
            for path, payload in before.items():
                self.assertEqual(after[path], payload, path)
        finally:
            temporary.cleanup()

    def test_no_forbidden_imports_or_rendering(self):
        source = (ROOT / "tools" / "asset-registry"
                  / "extract_images.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            match = re.match(r"\s*(import|from)\s+(\S+)", line)
            if not match:
                continue
            module = match.group(2).split(".")[0]
            self.assertNotIn(module, ("get_game_config", "jsonpatch", "flask",
                                      "server", "command", "engine",
                                      "requests", "subprocess", "socket",
                                      "urllib", "webbrowser", "http",
                                      "shutil", "PIL", "cv2", "numpy"),
                             "forbidden import: " + line)
        self.assertNotIn("Popen", source)
        self.assertNotIn("os.system", source)


if __name__ == "__main__":
    unittest.main()
