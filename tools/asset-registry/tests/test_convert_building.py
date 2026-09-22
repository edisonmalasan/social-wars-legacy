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

import convert_building as converter


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


class BitWriter:
    """MSB-first SWF bit-stream builder for synthetic shape records."""

    def __init__(self):
        self.bits = ""

    def write(self, value, count):
        self.bits += format(value, "0%db" % count)

    def bytes(self):
        padding = (-len(self.bits)) % 8
        stream = self.bits + "0" * padding
        return int(stream, 2).to_bytes(len(stream) // 8, "big")

    def bit_string(self):
        return self.bits


def solid_fill(red, green, blue):
    return bytes([0x00, red, green, blue])


def bitmap_fill(bitmap_id, matrix=b"\x84\x04"):
    return bytes([0x41]) + struct.pack("<H", bitmap_id) + matrix


def shape_payload(shape_id, bounds, fills, lines, record_bits, fill_bits=1,
                  line_bits=0):
    payload = struct.pack("<H", shape_id) + bounds
    payload += bytes([len(fills)]) + b"".join(fills)
    payload += bytes([len(lines)]) + b"".join(lines)
    writer = BitWriter()
    writer.write(fill_bits, 4)
    writer.write(line_bits, 4)
    stream = writer.bit_string() + record_bits
    stream += "0" * ((-len(stream)) % 8)
    return payload + int(stream, 2).to_bytes(len(stream) // 8, "big")


def style_change_record(move=False, fill0=None, fill1=None, line=None,
                        fill_bits=1, line_bits=0):
    writer = BitWriter()
    writer.write(0, 1)
    flags = ((1 if move else 0)
             | ((1 if fill0 is not None else 0) << 1)
             | ((1 if fill1 is not None else 0) << 2)
             | ((1 if line is not None else 0) << 3))
    writer.write(flags, 5)
    if move:
        writer.write(0, 5)
    if fill0 is not None:
        writer.write(fill0, fill_bits)
    if fill1 is not None:
        writer.write(fill1, fill_bits)
    if line is not None:
        writer.write(line, line_bits)
    return writer.bit_string()


def straight_record(nbits=2):
    writer = BitWriter()
    writer.write(1, 1)
    writer.write(1, 1)
    writer.write(nbits - 2, 4)
    writer.write(1, 1)
    writer.write(0, 2 * nbits)
    return writer.bit_string()


def end_record_bits():
    return "000000"


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


def snapshot(root):
    return {str(path.relative_to(root)).replace("\\", "/"):
            ("directory" if path.is_dir() else path.read_bytes())
            for path in Path(root).rglob("*")}


def run_main(argv):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = converter.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def make_fixture_tree(shape_tag=2):
    """Synthetic repo root: one house-like SWF with staged inputs."""
    temporary = tempfile.TemporaryDirectory()
    work = Path(temporary.name) / "repo"
    bounds = rect_bytes(200, 100)
    shape = shape_payload(
        2, bounds,
        [solid_fill(255, 0, 0), bitmap_fill(7)],
        [struct.pack("<H", 20) + b"\x00\x00\x00"],
        style_change_record(move=True, fill1=1, fill_bits=2)
        + straight_record() + end_record_bits(),
        fill_bits=2)
    swf = make_swf([tag(shape_tag, shape),
                    tag(76, struct.pack("<H", 1) + struct.pack("<H", 2)
                        + b"house_sym\x00")])
    target = work / "assets" / "sprites" / "0001_house_1_m.swf"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(swf)
    normalized = work / "packages" / "game-content" / "normalized"
    normalized.mkdir(parents=True)
    (normalized / "buildings.json").write_text(json.dumps([{
        "legacy_id": "1", "img_name": "0001_house_1_m", "width": 2,
        "height": 2, "name": "House I",
    }]), encoding="utf-8")
    tools = work / "tools" / "asset-registry"
    (tools / "schemas").mkdir(parents=True)
    for name in ("building_package.schema.json", "conversion.schema.json"):
        shutil.copy2(ROOT / "tools" / "asset-registry" / "schemas" / name,
                     tools / "schemas" / name)
    (tools / "inspection.json").write_text(json.dumps({
        "schema_version": 1, "policy": "swf-inspection-v1", "result": "success",
        "inputs": {}, "counts": {},
        "entries": {"assets/sprites/0001_house_1_m.swf":
                    {"symbols": ["house_sym"]}},
    }), encoding="utf-8")
    bitmap_bytes = b"BITMAP-7"
    extracted = work / "assets" / "converted" / "images" / "0001_house_1_m"
    extracted.mkdir(parents=True)
    (extracted / "7.jpg").write_bytes(bitmap_bytes)
    (tools / "image_extraction.json").write_text(json.dumps({
        "schema_version": 1, "policy": "bitmap-extraction-v1", "result": "success",
        "inputs": {}, "counts": {},
        "bitmaps": [{
            "source": "assets/sprites/0001_house_1_m.swf", "tag": 35,
            "character_id": 7, "family": "jpeg3", "format": 0,
            "width": 3, "height": 2,
            "outputs": [{
                "file": "assets/converted/images/0001_house_1_m/7.jpg",
                "bytes": len(bitmap_bytes),
                "sha256": hashlib.sha256(bitmap_bytes).hexdigest(),
            }],
        }],
    }), encoding="utf-8")
    return temporary, work


def read_out_json(out, relative):
    return json.loads((out / relative).read_text(encoding="utf-8"))


class SyntheticAssemblyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary, cls.work = make_fixture_tree()
        cls.addClassCleanup(cls.temporary.cleanup)
        code, stdout, _ = run_main(["--repo-root", str(cls.work),
                                    "--out-root", str(cls.work)])
        assert code == 0, stdout
        cls.package = read_out_json(
            cls.work, "assets/converted/buildings/0001_house_1_m/package.json")
        cls.document = read_out_json(
            cls.work, "tools/asset-registry/conversions.json")
        cls.statuses = read_out_json(
            cls.work, "tools/asset-registry/statuses.json")

    def test_package_identity_and_content_ref(self):
        self.assertEqual(self.package["legacy_id"], "0001_house_1_m")
        self.assertEqual(self.package["kind"], "converted_building")
        self.assertEqual(self.package["source_file"],
                         "assets/sprites/0001_house_1_m.swf")
        self.assertEqual(self.package["content_ref"]["name"], "House I")
        self.assertEqual(self.package["placement"], {"width": 2, "height": 2})
        self.assertEqual(self.package["symbols"], ["house_sym"])

    def test_shape_bounds_and_styles(self):
        self.assertEqual(len(self.package["shapes"]), 1)
        shape = self.package["shapes"][0]
        self.assertEqual(shape["character_id"], 2)
        self.assertEqual(shape["tag"], 2)
        self.assertEqual(shape["bounds"]["width_px"], 10)
        self.assertEqual(shape["bounds"]["height_px"], 5)
        kinds = sorted(str(fill.get("bitmap_id", "solid")) for fill in shape["fills"])
        self.assertEqual(kinds, ["7", "solid"])
        self.assertEqual(len(shape["lines"]), 1)
        self.assertEqual(shape["records"]["straight"], 1)
        self.assertEqual(shape["records"]["end"], 1)

    def test_bitmap_copies_match_extraction(self):
        self.assertEqual(len(self.package["bitmaps"]), 1)
        bitmap = self.package["bitmaps"][0]
        self.assertEqual(bitmap["character_id"], 7)
        data = (self.work / bitmap["file"]).read_bytes()
        self.assertEqual(data, b"BITMAP-7")
        self.assertEqual(bitmap["sha256"],
                         hashlib.sha256(b"BITMAP-7").hexdigest())

    def test_manifest_and_statuses(self):
        self.assertEqual(self.document["counts"]["packages"], 1)
        self.assertEqual(self.document["packages"][0]["legacy_id"],
                         "0001_house_1_m")
        self.assertEqual(self.statuses["statuses"],
                         {"assets/sprites/0001_house_1_m.swf": "converted"})
        self.assertEqual(self.statuses["policy"], "asset-statuses-v1")


class SyntheticFailureTests(unittest.TestCase):
    def build(self, mutate):
        temporary, work = make_fixture_tree()
        self.addCleanup(temporary.cleanup)
        mutate(work)
        return run_main(["--repo-root", str(work), "--out-root", str(work)])

    def test_unresolvable_bitmap_fill_exit_1(self):
        def mutate(work):
            document = read_out_json(work, "tools/asset-registry/image_extraction.json")
            document["bitmaps"] = []
            (work / "tools" / "asset-registry" / "image_extraction.json").write_text(
                json.dumps(document), encoding="utf-8")
        code, stdout, _ = self.build(mutate)
        self.assertEqual(code, 1)
        self.assertIn("unresolvable bitmap fill",
                      " ".join(json.loads(stdout)["problems"]))

    def test_missing_content_ref_exit_1(self):
        def mutate(work):
            (work / "packages" / "game-content" / "normalized"
             / "buildings.json").write_text(json.dumps(
                 [{"legacy_id": "9", "img_name": "other_house"}]),
                encoding="utf-8")
        code, stdout, _ = self.build(mutate)
        self.assertEqual(code, 1)
        self.assertIn("content ref", " ".join(json.loads(stdout)["problems"]))

    def test_unsupported_shape_tag_exit_1(self):
        temporary, work = make_fixture_tree(shape_tag=83)
        self.addCleanup(temporary.cleanup)
        code, stdout, _ = run_main(["--repo-root", str(work),
                                    "--out-root", str(work)])
        self.assertEqual(code, 1)
        self.assertIn("unsupported shape tag",
                      " ".join(json.loads(stdout)["problems"]))

    def test_truncated_swf_exit_1(self):
        def mutate(work):
            payload = (work / "assets" / "sprites" / "0001_house_1_m.swf").read_bytes()
            (work / "assets" / "sprites" / "0001_house_1_m.swf").write_bytes(
                payload[:-12])
        code, stdout, _ = self.build(mutate)
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
        def mutate(work):
            (work / "packages" / "game-content" / "normalized"
             / "buildings.json").write_text(json.dumps(
                 [{"legacy_id": "9", "img_name": "other_house"}]),
                encoding="utf-8")
        temporary, work = make_fixture_tree()
        self.addCleanup(temporary.cleanup)
        mutate(work)
        code, _, _ = run_main(["--repo-root", str(work),
                               "--out-root", str(work)])
        self.assertEqual(code, 1)
        self.assertFalse((work / "assets" / "converted" / "buildings").exists())
        self.assertFalse((work / "tools" / "asset-registry"
                          / "conversions.json").exists())


class RealHouseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.out = Path(cls.temporary.name) / "out"
        (cls.out / "assets" / "converted").mkdir(parents=True)
        (cls.out / "tools" / "asset-registry").mkdir(parents=True)

    def test_real_house_package(self):
        code, stdout, _ = run_main(["--repo-root", str(ROOT),
                                    "--out-root", str(self.out)])
        self.assertEqual(code, 0, stdout)
        package = read_out_json(
            self.out, "assets/converted/buildings/0001_house_1_m/package.json")
        self.assertEqual(package["legacy_id"], "0001_house_1_m")
        self.assertEqual(package["content_ref"]["name"], "House I")
        self.assertEqual(package["placement"], {"width": 2, "height": 2})
        self.assertEqual((package["frame_width"], package["frame_height"],
                          package["frame_rate"], package["frame_count"]),
                         (550, 400, 24.0, 1))
        self.assertEqual(package["symbols"], ["0001_house_1_m"])
        self.assertEqual(len(package["shapes"]), 1)
        shape = package["shapes"][0]
        self.assertEqual(shape["bounds"]["width_px"], 216)
        self.assertEqual(shape["bounds"]["height_px"], 144)
        bitmap_ids = sorted(fill["bitmap_id"] for fill in shape["fills"]
                            if "bitmap_id" in fill)
        self.assertEqual(bitmap_ids, [1])
        self.assertEqual(shape["records"]["straight"], 4)
        self.assertEqual(shape["records"]["end"], 1)
        self.assertEqual(len(package["bitmaps"]), 2)
        for bitmap in package["bitmaps"]:
            data = (self.out / bitmap["file"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), bitmap["sha256"])
        names = sorted((self.out / "assets" / "converted" / "buildings"
                        / "0001_house_1_m").iterdir())
        self.assertEqual([path.name for path in names],
                         ["1.jpg", "1_alpha.png", "package.json"])

    def test_registry_outputs_untouched(self):
        before = {}
        for name in ("registry.json", "coverage.json", "inspection.json",
                     "extraction.json", "image_extraction.json"):
            path = ROOT / "tools" / "asset-registry" / name
            before[name] = path.read_bytes()
        code, _, _ = run_main(["--repo-root", str(ROOT),
                               "--out-root", str(self.out)])
        self.assertEqual(code, 0)
        for name, payload in before.items():
            self.assertEqual((ROOT / "tools" / "asset-registry" / name).read_bytes(),
                             payload, name)


class TraceabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package_schema = json.loads(
            (ROOT / "tools" / "asset-registry" / "schemas"
             / "building_package.schema.json").read_text(encoding="utf-8"))
        cls.conversion_schema = json.loads(
            (ROOT / "tools" / "asset-registry" / "schemas"
             / "conversion.schema.json").read_text(encoding="utf-8"))
        temporary, work = make_fixture_tree()
        cls.addClassCleanup(temporary.cleanup)
        code, stdout, _ = run_main(["--repo-root", str(work),
                                    "--out-root", str(work)])
        assert code == 0, stdout
        cls.package = read_out_json(
            work, "assets/converted/buildings/0001_house_1_m/package.json")
        cls.document = read_out_json(
            work, "tools/asset-registry/conversions.json")

    def test_every_required_field_is_enforced(self):
        for schema, item, label in (
                (self.package_schema, self.package, "converted_building"),
                (self.conversion_schema, self.document, "conversion")):
            for field in schema["required"]:
                mutated = dict(item)
                del mutated[field]
                problems = converter.validate_against_schema(
                    mutated, schema, label)
                self.assertTrue(
                    any("missing required field" in problem
                        and field in problem for problem in problems),
                    "no validator check for required field %s.%s"
                    % (label, field))

    def test_wrong_types_are_rejected(self):
        mutated = dict(self.package)
        mutated["frame_width"] = "550"
        self.assertTrue(converter.validate_against_schema(
            mutated, self.package_schema, "converted_building"))
        mutated = dict(self.package)
        mutated["kind"] = "converted_unit"
        self.assertTrue(converter.validate_against_schema(
            mutated, self.package_schema, "converted_building"))
        mutated = dict(self.package)
        mutated["placement"] = [2, 2]
        self.assertTrue(converter.validate_against_schema(
            mutated, self.package_schema, "converted_building"))

    def test_digest_format_enforced(self):
        problems = []
        converter.validate_digest("xyz", "probe", problems)
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
        temporary, work = make_fixture_tree()
        try:
            code, _, _, opened, before = self.guarded_run(
                work, ["--repo-root", str(work), "--out-root", str(work)])
            self.assertEqual(code, 0)
            reads, writes = self.observed_sets(work, opened)
            self.assertEqual(writes, {
                "assets/converted/buildings/0001_house_1_m/package.json",
                "assets/converted/buildings/0001_house_1_m/7.jpg",
                "tools/asset-registry/conversions.json",
                "tools/asset-registry/statuses.json",
            })
            self.assertEqual(reads, {
                "assets/sprites/0001_house_1_m.swf",
                "assets/converted/images/0001_house_1_m/7.jpg",
                "packages/game-content/normalized/buildings.json",
                "tools/asset-registry/inspection.json",
                "tools/asset-registry/image_extraction.json",
                "tools/asset-registry/schemas/building_package.schema.json",
                "tools/asset-registry/schemas/conversion.schema.json",
            })
            after = snapshot(work)
            new_files = {path for path in set(after) - set(before)
                         if after[path] != "directory"}
            self.assertEqual(new_files, {
                "assets/converted/buildings/0001_house_1_m/package.json",
                "assets/converted/buildings/0001_house_1_m/7.jpg",
                "tools/asset-registry/conversions.json",
                "tools/asset-registry/statuses.json",
            })
            for path, payload in before.items():
                self.assertEqual(after[path], payload, path)
        finally:
            temporary.cleanup()

    def test_no_forbidden_imports_or_rendering(self):
        source = (ROOT / "tools" / "asset-registry"
                  / "convert_building.py").read_text(encoding="utf-8")
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
