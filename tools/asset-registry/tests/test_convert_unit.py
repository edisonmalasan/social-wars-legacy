import contextlib
import hashlib
import io
import json
import re
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "asset-registry"))

import convert_building as building_converter
import convert_unit as unit_converter

from test_convert_building import (
    bitmap_fill,
    end_record_bits,
    make_fixture_tree,
    make_swf,
    read_out_json,
    rect_bytes,
    shape_payload,
    snapshot,
    style_change_record,
    straight_record,
    tag,
)

ELEPHANT_SOURCE = "assets/sprites/10033_wild_elephant.swf"
HOUSE_SOURCE = "assets/sprites/0001_house_1_m.swf"
UNIT_BITMAP = b"UNIT-BITMAP"
UNIT_PACKAGE_PATH = "assets/converted/units/10033_wild_elephant/package.json"


def run_unit(argv):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = unit_converter.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def run_building(argv):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = building_converter.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def elephant_swf(sprite_declared=3, sprite_body=None, fill1=2, fill_bits=2,
                 root_body=None, shape_tag=2):
    """Synthetic unit source: one bitmap shape plus a labeled sprite.

    The second fill's MATRIX consumes seven bits so the fill-style array
    ends mid-byte, exercising the shared byte-alignment rule; the first
    fill is an unreferenced 65535 placeholder resolved by `fill1`.
    """
    shape = shape_payload(
        2, rect_bytes(200, 100),
        [bitmap_fill(65535), bitmap_fill(7, matrix=b"\x00")],
        [struct.pack("<H", 20) + b"\x00\x00\x00"],
        style_change_record(move=True, fill1=fill1, fill_bits=fill_bits)
        + straight_record() + end_record_bits(),
        fill_bits=fill_bits)
    if sprite_body is None:
        sprite_body = (
            tag(43, b"QUIETO\x00")
            + tag(26, bytes([0x06]) + struct.pack("<HH", 1, 2) + b"\x00\x00")
            + tag(1, b"")
            + tag(26, bytes([0x01]) + struct.pack("<H", 1))
            + tag(28, struct.pack("<H", 1))
            + tag(1, b"")
            + tag(1, b"")
            + tag(0, b""))
    sprite = tag(39, struct.pack("<HH", 10, sprite_declared) + sprite_body)
    symbol = tag(76, struct.pack("<H", 1) + struct.pack("<H", 10)
                 + b"10033_wild_elephant\x00")
    if root_body is None:
        root_body = (tag(26, bytes([0x06]) + struct.pack("<HH", 1, 10)
                         + b"\x00\x00") + tag(1, b""))
    return make_swf([tag(shape_tag, shape), sprite, symbol, root_body])


def rewrite_json(path, mutate):
    document = json.loads(path.read_text(encoding="utf-8"))
    mutate(document)
    path.write_text(json.dumps(document), encoding="utf-8")


def add_unit_files(work):
    """Stage the synthetic unit source and its inputs under `work`."""
    tools = work / "tools" / "asset-registry"
    schemas = tools / "schemas"
    schemas.mkdir(parents=True, exist_ok=True)
    for name in ("unit_package.schema.json", "conversion.schema.json"):
        source = ROOT / "tools" / "asset-registry" / "schemas" / name
        target = schemas / name
        target.write_bytes(source.read_bytes())
    source_path = work / "assets" / "sprites" / "10033_wild_elephant.swf"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(elephant_swf())
    normalized = work / "packages" / "game-content" / "normalized"
    normalized.mkdir(parents=True, exist_ok=True)
    (normalized / "units.json").write_text(json.dumps([{
        "legacy_id": "933", "img_name": "10033_wild_elephant",
        "name": "Wild Elephant", "width": 1, "height": 1,
    }]), encoding="utf-8")
    inspection_path = tools / "inspection.json"
    if inspection_path.exists():
        inspection = json.loads(inspection_path.read_text(encoding="utf-8"))
    else:
        inspection = {"schema_version": 1, "policy": "swf-inspection-v1",
                      "result": "success", "inputs": {}, "counts": {},
                      "entries": {}}
    inspection.setdefault("entries", {})[ELEPHANT_SOURCE] = {
        "symbols": ["10033_wild_elephant"],
        "sprite_count": 1,
        "frame_labels": ["QUIETO"],
    }
    inspection_path.write_text(json.dumps(inspection), encoding="utf-8")
    extraction_path = tools / "image_extraction.json"
    if extraction_path.exists():
        extraction = json.loads(extraction_path.read_text(encoding="utf-8"))
    else:
        extraction = {"schema_version": 1, "policy": "bitmap-extraction-v1",
                      "result": "success", "inputs": {}, "counts": {},
                      "bitmaps": []}
    extraction.setdefault("bitmaps", []).append({
        "source": ELEPHANT_SOURCE, "tag": 35, "character_id": 7,
        "family": "jpeg3", "format": 0, "width": 3, "height": 2,
        "outputs": [{
            "file": "assets/converted/images/10033_wild_elephant/7.jpg",
            "bytes": len(UNIT_BITMAP),
            "sha256": hashlib.sha256(UNIT_BITMAP).hexdigest(),
        }],
    })
    extraction_path.write_text(json.dumps(extraction), encoding="utf-8")
    extracted = (work / "assets" / "converted" / "images"
                 / "10033_wild_elephant")
    extracted.mkdir(parents=True, exist_ok=True)
    (extracted / "7.jpg").write_bytes(UNIT_BITMAP)


def make_unit_fixture_tree():
    """Synthetic repo root with only the unit source and its inputs."""
    temporary = tempfile.TemporaryDirectory()
    work = Path(temporary.name) / "repo"
    add_unit_files(work)
    return temporary, work


def make_dual_fixture_tree():
    """Synthetic repo root holding both the house and the unit sources."""
    temporary, work = make_fixture_tree()
    add_unit_files(work)
    return temporary, work


def legacy_document(extra_entries=()):
    building_entry = {
        "legacy_id": "0001_house_1_m",
        "directory": "assets/converted/buildings/0001_house_1_m",
        "package_sha256": "ab" * 32,
        "bitmaps": 2,
    }
    return {
        "schema_version": 1,
        "policy": "building-conversion-v1",
        "result": "success",
        "inputs": {
            "content_version": "cafebabe",
            "buildings": "packages/game-content/normalized/buildings.json",
            "inspection": "tools/asset-registry/inspection.json",
            "extraction": "tools/asset-registry/image_extraction.json",
        },
        "counts": {"packages": 1 + len(extra_entries), "output_bytes": 11733},
        "packages": [building_entry] + list(extra_entries),
    }


class SyntheticAssemblyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary, cls.work = make_unit_fixture_tree()
        cls.addClassCleanup(cls.temporary.cleanup)
        code, stdout, _ = run_unit(["--repo-root", str(cls.work),
                                    "--out-root", str(cls.work)])
        assert code == 0, stdout
        cls.package = read_out_json(cls.work, UNIT_PACKAGE_PATH)
        cls.document = read_out_json(
            cls.work, "tools/asset-registry/conversions.json")
        cls.statuses = read_out_json(
            cls.work, "tools/asset-registry/statuses.json")

    def test_identity_and_content_ref(self):
        self.assertEqual(self.package["legacy_id"], "10033_wild_elephant")
        self.assertEqual(self.package["kind"], "converted_unit")
        self.assertEqual(self.package["source_file"], ELEPHANT_SOURCE)
        self.assertEqual(self.package["source_layer"],
                         "converted(asset-registry)")
        self.assertEqual(self.package["content_ref"], {
            "legacy_id": "933", "img_name": "10033_wild_elephant",
            "name": "Wild Elephant", "width": 1, "height": 1,
        })
        self.assertEqual(self.package["symbols"],
                         [{"id": 10, "name": "10033_wild_elephant"}])

    def test_frame_data(self):
        self.assertEqual((self.package["frame_width"],
                          self.package["frame_height"],
                          self.package["frame_rate"],
                          self.package["frame_count"]),
                         (100, 100, 24.0, 1))

    def test_timeline_inventory(self):
        self.assertEqual(len(self.package["sprites"]), 1)
        sprite = self.package["sprites"][0]
        self.assertEqual(sprite["sprite_id"], 10)
        self.assertEqual(sprite["frame_count"], 3)
        self.assertEqual(sprite["labels"],
                         [{"name": "QUIETO", "frame": 1, "anchor": False}])
        self.assertEqual(sprite["placements"], [
            {"frame": 1, "depth": 1, "character_id": 2,
             "character_kind": "shape", "move": False},
            {"frame": 2, "depth": 1, "character_id": None,
             "character_kind": None, "move": True},
        ])
        self.assertEqual(sprite["removes"], [{"frame": 2, "depth": 1}])
        main = self.package["main"]
        self.assertEqual(main["frame_count"], 1)
        self.assertEqual(main["labels"], [])
        self.assertEqual(main["removes"], [])
        self.assertEqual(main["placements"], [
            {"frame": 1, "depth": 1, "character_id": 10,
             "character_kind": "sprite", "move": False},
        ])

    def test_shape_records_and_placeholders(self):
        self.assertEqual(len(self.package["shapes"]), 1)
        shape = self.package["shapes"][0]
        self.assertEqual(shape["character_id"], 2)
        self.assertEqual(shape["tag"], 2)
        self.assertEqual(shape["bounds"]["width_px"], 10)
        self.assertEqual(shape["bounds"]["height_px"], 5)
        self.assertEqual(len(shape["fills"]), 2)
        self.assertEqual(shape["fills"][0]["bitmap_id"], 65535)
        self.assertEqual(shape["fills"][1]["bitmap_id"], 7)
        # Mid-byte MATRIX recorded verbatim as one raw byte.
        self.assertEqual(shape["fills"][1]["matrix"], "00")
        self.assertEqual(shape["fill_refs"], [2])
        self.assertEqual(len(shape["lines"]), 1)
        self.assertEqual(shape["records"]["style_change"], 1)
        self.assertEqual(shape["records"]["straight"], 1)
        self.assertEqual(shape["records"]["end"], 1)

    def test_bitmap_copy_matches_extraction(self):
        self.assertEqual(self.package["bitmaps"], [{
            "character_id": 7,
            "file": "assets/converted/units/10033_wild_elephant/7.jpg",
            "bytes": len(UNIT_BITMAP),
            "sha256": hashlib.sha256(UNIT_BITMAP).hexdigest(),
        }])
        copied = (self.work / self.package["bitmaps"][0]["file"]).read_bytes()
        self.assertEqual(copied, UNIT_BITMAP)

    def test_manifest_and_statuses(self):
        self.assertEqual(self.document["policy"], "conversion-v1")
        self.assertEqual(self.document["counts"]["packages"], 1)
        entry = self.document["packages"][0]
        self.assertEqual(entry["legacy_id"], "10033_wild_elephant")
        self.assertEqual(entry["policy"], "unit-conversion-v1")
        self.assertEqual(entry["directory"],
                         "assets/converted/units/10033_wild_elephant")
        package_bytes = (self.work / UNIT_PACKAGE_PATH).stat().st_size
        self.assertEqual(entry["output_bytes"],
                         package_bytes + len(UNIT_BITMAP))
        payload = (self.work / UNIT_PACKAGE_PATH).read_bytes()
        self.assertEqual(hashlib.sha256(payload).hexdigest(),
                         entry["package_sha256"])
        self.assertEqual(self.document["counts"]["output_bytes"],
                         entry["output_bytes"])
        self.assertEqual(sorted(self.document["inputs"]), [
            "extraction", "inspection", "units", "units_content_version"])
        self.assertEqual(self.statuses["policy"], "asset-statuses-v1")
        self.assertEqual(self.statuses["statuses"],
                         {ELEPHANT_SOURCE: "converted"})

    def test_reruns_byte_identical(self):
        before = snapshot(self.work)
        code, stdout, _ = run_unit(["--repo-root", str(self.work),
                                    "--out-root", str(self.work)])
        self.assertEqual(code, 0, stdout)
        self.assertEqual(snapshot(self.work), before)


class SyntheticFailureTests(unittest.TestCase):
    def build(self, mutate, runner=run_unit):
        temporary, work = make_unit_fixture_tree()
        self.addCleanup(temporary.cleanup)
        mutate(work)
        before = snapshot(work)
        code, stdout, stderr = runner(["--repo-root", str(work),
                                       "--out-root", str(work)])
        self.assertEqual(snapshot(work), before,
                         "failed run must write nothing")
        return code, stdout, stderr

    def test_unsupported_timeline_tag(self):
        def mutate(work):
            body = (tag(43, b"QUIETO\x00") + tag(70, b"\x00\x00")
                    + tag(1, b"") + tag(1, b"") + tag(1, b"")
                    + tag(0, b""))
            (work / "assets" / "sprites" / "10033_wild_elephant.swf").write_bytes(
                elephant_swf(sprite_body=body))
        code, stdout, _ = self.build(mutate)
        self.assertEqual(code, 1)
        self.assertIn("unsupported timeline tag", stdout)
        self.assertIn("sprite 10", stdout)

    def test_unknown_root_tag(self):
        def mutate(work):
            (work / "assets" / "sprites" / "10033_wild_elephant.swf").write_bytes(
                elephant_swf(root_body=tag(99, b"") + tag(1, b"")))
        code, stdout, _ = self.build(mutate)
        self.assertEqual(code, 1)
        self.assertIn("unsupported tag in timeline", stdout)
        self.assertIn("code 99", stdout)

    def test_undefined_character_reference(self):
        def mutate(work):
            body = (tag(43, b"QUIETO\x00")
                    + tag(26, bytes([0x06]) + struct.pack("<HH", 1, 99)
                          + b"\x00\x00")
                    + tag(1, b"") + tag(1, b"") + tag(1, b"")
                    + tag(0, b""))
            (work / "assets" / "sprites" / "10033_wild_elephant.swf").write_bytes(
                elephant_swf(sprite_body=body))
        code, stdout, _ = self.build(mutate)
        self.assertEqual(code, 1)
        self.assertIn("references undefined character 99", stdout)

    def test_sprite_frame_count_mismatch(self):
        def mutate(work):
            (work / "assets" / "sprites" / "10033_wild_elephant.swf").write_bytes(
                elephant_swf(sprite_declared=2))
        code, stdout, _ = self.build(mutate)
        self.assertEqual(code, 1)
        self.assertIn(
            "declared frame count mismatch for sprite 10: declared 2 "
            "observed 3", stdout)

    def test_main_frame_count_mismatch(self):
        def mutate(work):
            (work / "assets" / "sprites" / "10033_wild_elephant.swf").write_bytes(
                elephant_swf(root_body=tag(
                    26, bytes([0x06]) + struct.pack("<HH", 1, 10)
                    + b"\x00\x00")))
        code, stdout, _ = self.build(mutate)
        self.assertEqual(code, 1)
        self.assertIn(
            "declared frame count mismatch for main timeline: declared 1 "
            "observed 0", stdout)

    def test_label_mismatch_against_inspection(self):
        def mutate(work):
            rewrite_json(work / "tools" / "asset-registry" / "inspection.json",
                         lambda doc: doc["entries"][ELEPHANT_SOURCE].update(
                             frame_labels=["ANDAR"]))
        code, stdout, _ = self.build(mutate)
        self.assertEqual(code, 1)
        self.assertIn("frame label mismatch against inspection", stdout)

    def test_sprite_count_mismatch_against_inspection(self):
        def mutate(work):
            rewrite_json(work / "tools" / "asset-registry" / "inspection.json",
                         lambda doc: doc["entries"][ELEPHANT_SOURCE].update(
                             sprite_count=2))
        code, stdout, _ = self.build(mutate)
        self.assertEqual(code, 1)
        self.assertIn("sprite count mismatch", stdout)

    def test_inspection_sprite_count_not_integer(self):
        def mutate(work):
            rewrite_json(work / "tools" / "asset-registry" / "inspection.json",
                         lambda doc: doc["entries"][ELEPHANT_SOURCE].update(
                             sprite_count="1"))
        code, stdout, _ = self.build(mutate)
        self.assertEqual(code, 1)
        self.assertIn("inspection sprite count not integer", stdout)

    def test_content_ref_not_unique(self):
        def mutate(work):
            path = (work / "packages" / "game-content" / "normalized"
                    / "units.json")
            entries = json.loads(path.read_text(encoding="utf-8"))
            entries[0]["legacy_id"] = "994"
            path.write_text(json.dumps(entries), encoding="utf-8")
        code, stdout, _ = self.build(mutate)
        self.assertEqual(code, 1)
        self.assertIn("content ref not unique for unit 10033_wild_elephant",
                      stdout)
        self.assertIn(": 0", stdout)

    def test_missing_inspection_entry(self):
        def mutate(work):
            rewrite_json(work / "tools" / "asset-registry" / "inspection.json",
                         lambda doc: doc["entries"].pop(ELEPHANT_SOURCE))
        code, stdout, _ = self.build(mutate)
        self.assertEqual(code, 1)
        self.assertIn("inspection entry missing for " + ELEPHANT_SOURCE,
                      stdout)

    def test_unresolvable_referenced_fill(self):
        def mutate(work):
            rewrite_json(
                work / "tools" / "asset-registry" / "image_extraction.json",
                lambda doc: doc.update(bitmaps=[]))
        code, stdout, _ = self.build(mutate)
        self.assertEqual(code, 1)
        self.assertIn("unresolvable bitmap fill at shape 2 -> 7", stdout)

    def test_placeholder_fill_referenced(self):
        def mutate(work):
            (work / "assets" / "sprites" / "10033_wild_elephant.swf").write_bytes(
                elephant_swf(fill1=1))
        code, stdout, _ = self.build(mutate)
        self.assertEqual(code, 1)
        self.assertIn(
            "referenced fill uses placeholder bitmap id 65535 at shape 2",
            stdout)

    def test_fill_index_out_of_range(self):
        def mutate(work):
            (work / "assets" / "sprites" / "10033_wild_elephant.swf").write_bytes(
                elephant_swf(fill1=3))
        code, stdout, _ = self.build(mutate)
        self.assertEqual(code, 1)
        self.assertIn("fill index out of range at shape 2: index 3 (2 fills)",
                      stdout)

    def test_bitmap_digest_mismatch(self):
        def mutate(work):
            rewrite_json(
                work / "tools" / "asset-registry" / "image_extraction.json",
                lambda doc: doc["bitmaps"][0]["outputs"][0].update(
                    sha256="0" * 64))
        code, stdout, _ = self.build(mutate)
        self.assertEqual(code, 1)
        self.assertIn("bitmap digest mismatch at "
                      "assets/converted/units/10033_wild_elephant/7.jpg",
                      stdout)

    def test_unsupported_shape_tag(self):
        def mutate(work):
            (work / "assets" / "sprites" / "10033_wild_elephant.swf").write_bytes(
                elephant_swf(shape_tag=83))
        code, stdout, _ = self.build(mutate)
        self.assertEqual(code, 1)
        self.assertIn("unsupported shape tag", stdout)

    def test_invalid_repository_root_exits_2(self):
        temporary, work = make_unit_fixture_tree()
        self.addCleanup(temporary.cleanup)
        missing = work / "does-not-exist"
        code, _stdout, stderr = run_unit(["--repo-root", str(missing),
                                          "--out-root", str(work)])
        self.assertEqual(code, 2)
        self.assertIn("repository root invalid", stderr)


class ManifestOrderTests(unittest.TestCase):
    def run_order(self, order):
        temporary, work = make_dual_fixture_tree()
        self.addCleanup(temporary.cleanup)
        for runner in order:
            code, stdout, stderr = runner(["--repo-root", str(work),
                                           "--out-root", str(work)])
            self.assertEqual(code, 0, stdout + stderr)
        payload = (work / "tools" / "asset-registry" / "conversions.json"
                   ).read_bytes()
        return payload, json.loads(payload.decode("utf-8")), work

    def test_both_orders_byte_identical(self):
        first_bytes, first, work_first = self.run_order(
            [run_building, run_unit])
        second_bytes, second, work_second = self.run_order(
            [run_unit, run_building])
        self.assertEqual(first_bytes, second_bytes)
        self.assertEqual(first, second)
        self.assertEqual(first["policy"], "conversion-v1")
        self.assertEqual(first["counts"]["packages"], 2)
        entries = first["packages"]
        self.assertEqual(sorted(entry["policy"] for entry in entries),
                         ["building-conversion-v1", "unit-conversion-v1"])
        self.assertEqual(first["counts"]["output_bytes"],
                         sum(entry["output_bytes"] for entry in entries))
        for work, document in ((work_first, first), (work_second, second)):
            for entry in document["packages"]:
                payload = (work / entry["directory"]
                           / "package.json").read_bytes()
                self.assertEqual(hashlib.sha256(payload).hexdigest(),
                                 entry["package_sha256"], entry["directory"])

    def test_statuses_merge_both_sources(self):
        _payload, _document, work = self.run_order([run_unit, run_building])
        statuses = read_out_json(work, "tools/asset-registry/statuses.json")
        self.assertEqual(statuses["statuses"],
                         {HOUSE_SOURCE: "converted",
                          ELEPHANT_SOURCE: "converted"})


class LegacyEnvelopeTests(unittest.TestCase):
    def write_legacy(self, work, document):
        path = work / "tools" / "asset-registry" / "conversions.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        return path

    def test_unit_rejects_legacy_without_writes(self):
        temporary, work = make_unit_fixture_tree()
        self.addCleanup(temporary.cleanup)
        path = self.write_legacy(work, legacy_document())
        before = snapshot(work)
        code, stdout, _ = run_unit(["--repo-root", str(work),
                                    "--out-root", str(work)])
        self.assertEqual(code, 1)
        self.assertIn("conversion manifest is legacy building-conversion-v1; "
                      "run convert_building.py to migrate it first", stdout)
        self.assertEqual(snapshot(work), before)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["policy"],
                         "building-conversion-v1")

    def test_building_migrates_legacy_envelope(self):
        temporary, work = make_dual_fixture_tree()
        self.addCleanup(temporary.cleanup)
        self.write_legacy(work, legacy_document())
        code, stdout, stderr = run_building(["--repo-root", str(work),
                                             "--out-root", str(work)])
        self.assertEqual(code, 0, stdout + stderr)
        document = read_out_json(work, "tools/asset-registry/conversions.json")
        self.assertEqual(document["policy"], "conversion-v1")
        self.assertEqual(len(document["packages"]), 1)
        entry = document["packages"][0]
        self.assertEqual(entry["legacy_id"], "0001_house_1_m")
        self.assertEqual(entry["policy"], "building-conversion-v1")
        payload = (work / entry["directory"] / "package.json").read_bytes()
        self.assertEqual(hashlib.sha256(payload).hexdigest(),
                         entry["package_sha256"])
        self.assertNotIn("content_version", document["inputs"])
        self.assertIn("buildings", document["inputs"])

    def test_building_refuses_foreign_legacy_entries(self):
        temporary, work = make_dual_fixture_tree()
        self.addCleanup(temporary.cleanup)
        foreign = {"legacy_id": "other", "directory": "assets/converted/other",
                   "package_sha256": "cd" * 32, "bitmaps": 1}
        self.write_legacy(work, legacy_document(extra_entries=[foreign]))
        before = snapshot(work)
        code, stdout, _ = run_building(["--repo-root", str(work),
                                        "--out-root", str(work)])
        self.assertEqual(code, 1)
        self.assertIn("legacy conversion manifest holds foreign entries; "
                      "refusing to migrate", stdout)
        self.assertEqual(snapshot(work), before)

    def test_unknown_envelope_policy_rejected(self):
        temporary, work = make_unit_fixture_tree()
        self.addCleanup(temporary.cleanup)
        self.write_legacy(work, {
            "schema_version": 1, "policy": "mystery-v9", "result": "success",
            "inputs": {}, "counts": {"packages": 0, "output_bytes": 0},
            "packages": [],
        })
        before = snapshot(work)
        code, stdout, _ = run_unit(["--repo-root", str(work),
                                    "--out-root", str(work)])
        self.assertEqual(code, 1)
        self.assertIn("conversion manifest policy not recognized: "
                      "'mystery-v9'", stdout)
        self.assertEqual(snapshot(work), before)

    def test_entry_without_output_bytes_rejected(self):
        temporary, work = make_unit_fixture_tree()
        self.addCleanup(temporary.cleanup)
        self.write_legacy(work, {
            "schema_version": 1, "policy": "conversion-v1",
            "result": "success", "inputs": {},
            "counts": {"packages": 1, "output_bytes": 0},
            "packages": [{"legacy_id": "other",
                          "directory": "assets/converted/other",
                          "package_sha256": "ef" * 32, "bitmaps": 1}],
        })
        before = snapshot(work)
        code, stdout, _ = run_unit(["--repo-root", str(work),
                                    "--out-root", str(work)])
        self.assertEqual(code, 1)
        self.assertIn("conversion manifest entry missing output_bytes: "
                      "assets/converted/other", stdout)
        self.assertEqual(snapshot(work), before)

    def test_v1_envelope_preserves_foreign_keys_verbatim(self):
        """A conversion-v1 envelope keeps foreign input keys and entries
        verbatim; only the legacy envelope drops the content_version key."""
        temporary, work = make_unit_fixture_tree()
        self.addCleanup(temporary.cleanup)
        foreign = {"legacy_id": "other",
                   "directory": "assets/converted/other",
                   "package_sha256": "12" * 32, "bitmaps": 1,
                   "output_bytes": 7, "policy": "building-conversion-v1"}
        self.write_legacy(work, {
            "schema_version": 1, "policy": "conversion-v1",
            "result": "success",
            "inputs": {"content_version": "keep-me",
                       "units": "packages/game-content/normalized/units.json"},
            "counts": {"packages": 1, "output_bytes": 7},
            "packages": [dict(foreign)],
        })
        code, stdout, stderr = run_unit(["--repo-root", str(work),
                                         "--out-root", str(work)])
        self.assertEqual(code, 0, stdout + stderr)
        document = read_out_json(work, "tools/asset-registry/conversions.json")
        self.assertEqual(document["inputs"]["content_version"], "keep-me")
        entries = {item["directory"]: item
                   for item in document["packages"]}
        self.assertEqual(entries["assets/converted/other"], foreign)
        self.assertEqual(document["counts"], {
            "packages": 2,
            "output_bytes": 7
            + entries["assets/converted/units/10033_wild_elephant"]
            ["output_bytes"],
        })


class RealElephantTests(unittest.TestCase):
    """Run the converter on the real corpus into a disposable out-root."""

    GUARDED = (
        ELEPHANT_SOURCE,
        "tools/asset-registry/inspection.json",
        "tools/asset-registry/image_extraction.json",
        "tools/asset-registry/statuses.json",
        "tools/asset-registry/conversions.json",
        "packages/game-content/normalized/units.json",
        "packages/game-content/normalized/buildings.json",
        "assets/converted/buildings/0001_house_1_m/package.json",
    )

    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.out = Path(cls.temporary.name)
        cls.before = {relative: (ROOT / relative).read_bytes()
                      for relative in cls.GUARDED}
        code, stdout, stderr = run_unit(["--repo-root", str(ROOT),
                                         "--out-root", str(cls.out)])
        assert code == 0, stdout + stderr
        cls.first = (cls.out / UNIT_PACKAGE_PATH).read_bytes()
        cls.first_manifest = (cls.out / "tools" / "asset-registry"
                              / "conversions.json").read_bytes()
        cls.first_statuses = (cls.out / "tools" / "asset-registry"
                              / "statuses.json").read_bytes()
        cls.package = json.loads(cls.first)
        code, stdout, stderr = run_unit(["--repo-root", str(ROOT),
                                         "--out-root", str(cls.out)])
        assert code == 0, stdout + stderr
        cls.second = (cls.out / UNIT_PACKAGE_PATH).read_bytes()

    def test_sources_and_registry_remain_byte_identical(self):
        for relative, payload in self.before.items():
            self.assertEqual((ROOT / relative).read_bytes(), payload,
                             relative)

    def test_frame_data_and_content_ref(self):
        self.assertEqual((self.package["frame_width"],
                          self.package["frame_height"],
                          self.package["frame_rate"],
                          self.package["frame_count"]),
                         (550, 400, 30.0, 1))
        content_ref = self.package["content_ref"]
        self.assertEqual(content_ref["legacy_id"], "933")
        self.assertEqual(content_ref["img_name"], "10033_wild_elephant")
        self.assertEqual(content_ref["name"], "Wild Elephant")

    def test_symbols_export_ids(self):
        self.assertEqual(self.package["symbols"], [
            {"id": 63, "name": "10033_wild_elephant"},
            {"id": 62,
             "name": "_10033_wild_elephant_fla.arquero1atacando3_4detras_7"},
        ])

    def test_sprite_63_inventory(self):
        sprites = {entry["sprite_id"]: entry
                   for entry in self.package["sprites"]}
        self.assertEqual(sorted(sprites), [19, 28, 37, 46, 55, 62, 63])
        sprite = sprites[63]
        self.assertEqual(sprite["frame_count"], 29)
        self.assertEqual([(label["name"], label["frame"])
                          for label in sprite["labels"]],
                         [("QUIETO", 1), ("ANDAR", 6), ("ATAQUE", 11),
                          ("MUERTE", 16), ("PICAR", 21)])
        self.assertEqual([(place["frame"], place["depth"],
                           place["character_id"], place["character_kind"])
                          for place in sprite["placements"]],
                         [(1, 1, 2, "shape"), (2, 1, 4, "shape"),
                          (3, 1, 6, "shape"), (4, 1, 8, "shape"),
                          (5, 1, 10, "shape"), (6, 1, 19, "sprite"),
                          (7, 1, 28, "sprite"), (8, 1, 37, "sprite"),
                          (9, 1, 46, "sprite"), (10, 1, 55, "sprite"),
                          (16, 1, 62, "sprite")])
        self.assertTrue(all(place["depth"] == 1
                            for place in sprite["placements"]))
        self.assertEqual([(remove["frame"], remove["depth"])
                          for remove in sprite["removes"]],
                         [(6, 1), (7, 1), (8, 1), (9, 1), (10, 1),
                          (11, 1), (21, 1)])

    def test_nested_sprite_frame_counts(self):
        sprites = {entry["sprite_id"]: entry
                   for entry in self.package["sprites"]}
        for sprite_id in (19, 28, 37, 46, 55):
            self.assertEqual(sprites[sprite_id]["frame_count"], 20)
            self.assertEqual(len(sprites[sprite_id]["placements"]), 5)
            self.assertEqual(sprites[sprite_id]["labels"], [])
        self.assertEqual(sprites[62]["frame_count"], 7)
        self.assertEqual(len(sprites[62]["placements"]), 3)

    def test_main_timeline(self):
        main = self.package["main"]
        self.assertEqual(main["frame_count"], 1)
        self.assertEqual(main["labels"], [])
        self.assertEqual(main["removes"], [])
        self.assertEqual([(place["frame"], place["depth"],
                           place["character_id"], place["character_kind"])
                          for place in main["placements"]],
                         [(1, 1, 63, "sprite")])

    def test_label_names_equal_inspection(self):
        inspection = json.loads(
            (ROOT / "tools" / "asset-registry" / "inspection.json"
             ).read_text(encoding="utf-8"))
        inspected = inspection["entries"][ELEPHANT_SOURCE]
        recorded = sorted(label["name"]
                          for entry in self.package["sprites"]
                          for label in entry["labels"])
        self.assertEqual(recorded, sorted(inspected["frame_labels"]))
        self.assertEqual(inspected["frame_labels"],
                         ["QUIETO", "ANDAR", "ATAQUE", "MUERTE", "PICAR"])
        self.assertEqual(inspected["sprite_count"], 7)

    def test_shape_records_and_placeholder_split(self):
        shapes = self.package["shapes"]
        self.assertEqual(len(shapes), 28)
        with_placeholder = [shape for shape in shapes
                            if any(fill.get("bitmap_id") == 65535
                                   for fill in shape["fills"])]
        self.assertEqual(len(with_placeholder), 25)
        self.assertEqual(len(shapes) - len(with_placeholder), 3)
        for shape in shapes:
            self.assertEqual(len(shape["fill_refs"]), 1)
            self.assertEqual(shape["records"]["new_styles"], 0)
            index = shape["fill_refs"][0]
            self.assertGreaterEqual(index, 1)
            self.assertLessEqual(index, len(shape["fills"]))
            self.assertNotEqual(shape["fills"][index - 1].get("bitmap_id"),
                                65535)

    def test_bitmap_copies_match_extraction(self):
        extraction = json.loads(
            (ROOT / "tools" / "asset-registry" / "image_extraction.json"
             ).read_text(encoding="utf-8"))
        expected = {}
        for bitmap in extraction["bitmaps"]:
            if bitmap.get("source") != ELEPHANT_SOURCE:
                continue
            for output in bitmap["outputs"]:
                expected[Path(output["file"]).name] = output
        self.assertEqual(len(self.package["bitmaps"]), 56)
        self.assertEqual(len({entry["character_id"]
                              for entry in self.package["bitmaps"]}), 28)
        names = {Path(entry["file"]).name
                 for entry in self.package["bitmaps"]}
        self.assertEqual(names, set(expected))
        for entry in self.package["bitmaps"]:
            output = expected[Path(entry["file"]).name]
            source_payload = (ROOT / output["file"]).read_bytes()
            copied = (self.out / entry["file"]).read_bytes()
            self.assertEqual(copied, source_payload)
            self.assertEqual(len(copied), entry["bytes"])
            self.assertEqual(hashlib.sha256(copied).hexdigest(),
                             entry["sha256"])
            self.assertEqual(entry["sha256"], output["sha256"])

    def test_reruns_byte_identical(self):
        self.assertEqual(self.first, self.second)
        out = self.out / "tools" / "asset-registry"
        self.assertEqual(self.first_manifest,
                         (out / "conversions.json").read_bytes())
        self.assertEqual(self.first_statuses,
                         (out / "statuses.json").read_bytes())

    def test_manifest_records_both_packages(self):
        document = json.loads(self.first_manifest.decode("utf-8"))
        self.assertEqual(document["policy"], "conversion-v1")
        self.assertEqual(document["counts"]["packages"], 2)
        entries = {entry["legacy_id"]: entry
                   for entry in document["packages"]}
        root_manifest = json.loads(
            (ROOT / "tools" / "asset-registry" / "conversions.json"
             ).read_text(encoding="utf-8"))
        root_entries = {entry["legacy_id"]: entry
                        for entry in root_manifest["packages"]}
        # The foreign building entry is preserved verbatim.
        self.assertEqual(entries["0001_house_1_m"],
                         root_entries["0001_house_1_m"])
        self.assertEqual(entries["0001_house_1_m"]["policy"],
                         "building-conversion-v1")
        self.assertEqual(entries["10033_wild_elephant"]["policy"],
                         "unit-conversion-v1")
        self.assertEqual(document["counts"]["output_bytes"],
                         sum(entry["output_bytes"]
                             for entry in document["packages"]))
        statuses = json.loads(self.first_statuses.decode("utf-8"))
        self.assertEqual(statuses["statuses"][ELEPHANT_SOURCE], "converted")
        self.assertEqual(statuses["statuses"][HOUSE_SOURCE], "converted")


class TraceabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package_schema = json.loads(
            (ROOT / "tools" / "asset-registry" / "schemas"
             / "unit_package.schema.json").read_text(encoding="utf-8"))
        cls.conversion_schema = json.loads(
            (ROOT / "tools" / "asset-registry" / "schemas"
             / "conversion.schema.json").read_text(encoding="utf-8"))
        cls.temporary, cls.work = make_unit_fixture_tree()
        cls.addClassCleanup(cls.temporary.cleanup)
        code, stdout, _ = run_unit(["--repo-root", str(cls.work),
                                    "--out-root", str(cls.work)])
        assert code == 0, stdout
        cls.package = read_out_json(cls.work, UNIT_PACKAGE_PATH)
        cls.document = read_out_json(
            cls.work, "tools/asset-registry/conversions.json")

    def clone(self):
        return json.loads(json.dumps(self.package))

    def test_every_required_field_is_enforced(self):
        for schema, item, label in (
                (self.package_schema, self.package, "converted_unit"),
                (self.conversion_schema, self.document, "conversion")):
            for field in schema["required"]:
                mutated = dict(item)
                del mutated[field]
                problems = building_converter.validate_against_schema(
                    mutated, schema, label)
                self.assertTrue(
                    any("missing required field" in problem
                        and field in problem for problem in problems),
                    "no validator check for required field %s.%s"
                    % (label, field))

    def test_nested_required_fields_are_enforced(self):
        mutated = self.clone()
        sprites = list(mutated["sprites"])
        first = dict(sprites[0])
        del first["sprite_id"]
        sprites[0] = first
        mutated["sprites"] = sprites
        problems = building_converter.validate_against_schema(
            mutated, self.package_schema, "converted_unit")
        self.assertTrue(any("sprites[0].sprite_id" in problem
                            for problem in problems))
        mutated = self.clone()
        del mutated["main"]["labels"]
        problems = building_converter.validate_against_schema(
            mutated, self.package_schema, "converted_unit")
        self.assertTrue(any("main.labels" in problem
                            for problem in problems))
        mutated = self.clone()
        placements = list(mutated["sprites"][0]["placements"])
        placement = dict(placements[0])
        del placement["depth"]
        placements[0] = placement
        sprites = list(mutated["sprites"])
        sprite = dict(sprites[0])
        sprite["placements"] = placements
        sprites[0] = sprite
        mutated["sprites"] = sprites
        problems = building_converter.validate_against_schema(
            mutated, self.package_schema, "converted_unit")
        self.assertTrue(any("sprites[0].placements[0].depth" in problem
                            for problem in problems))

    def test_wrong_types_are_rejected(self):
        mutated = self.clone()
        mutated["frame_width"] = "100"
        self.assertTrue(building_converter.validate_against_schema(
            mutated, self.package_schema, "converted_unit"))
        mutated = self.clone()
        mutated["kind"] = "converted_building"
        self.assertTrue(building_converter.validate_against_schema(
            mutated, self.package_schema, "converted_unit"))
        mutated = self.clone()
        mutated["main"] = [mutated["main"]]
        self.assertTrue(building_converter.validate_against_schema(
            mutated, self.package_schema, "converted_unit"))

    def test_nested_enum_is_enforced(self):
        mutated = self.clone()
        placements = list(mutated["sprites"][0]["placements"])
        placement = dict(placements[0])
        placement["character_kind"] = "effect"
        placements[0] = placement
        sprites = list(mutated["sprites"])
        sprite = dict(sprites[0])
        sprite["placements"] = placements
        sprites[0] = sprite
        mutated["sprites"] = sprites
        problems = building_converter.validate_against_schema(
            mutated, self.package_schema, "converted_unit")
        self.assertTrue(any("enum mismatch" in problem
                            for problem in problems))


class ContainmentTests(unittest.TestCase):
    def guarded_run(self, work, argv):
        opened = []
        real_io_open = io.open
        real_builtins_open = open

        def guarded_open(file, mode="r", *args, **kwargs):
            if any(flag in str(mode) for flag in ("w", "a", "x", "+")):
                opened.append(("write", str(file)))
            else:
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
            code, stdout, stderr = run_unit(argv)
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
        temporary, work = make_unit_fixture_tree()
        try:
            code, _, _, opened, before = self.guarded_run(
                work, ["--repo-root", str(work), "--out-root", str(work)])
            self.assertEqual(code, 0)
            reads, writes = self.observed_sets(work, opened)
            self.assertEqual(writes, {
                "assets/converted/units/10033_wild_elephant/package.json",
                "assets/converted/units/10033_wild_elephant/7.jpg",
                "tools/asset-registry/conversions.json",
                "tools/asset-registry/statuses.json",
            })
            self.assertEqual(reads, {
                ELEPHANT_SOURCE,
                "assets/converted/images/10033_wild_elephant/7.jpg",
                "packages/game-content/normalized/units.json",
                "tools/asset-registry/inspection.json",
                "tools/asset-registry/image_extraction.json",
                "tools/asset-registry/schemas/unit_package.schema.json",
                "tools/asset-registry/schemas/conversion.schema.json",
            })
            after = snapshot(work)
            new_files = {path for path in set(after) - set(before)
                         if after[path] != "directory"}
            self.assertEqual(new_files, {
                "assets/converted/units/10033_wild_elephant/package.json",
                "assets/converted/units/10033_wild_elephant/7.jpg",
                "tools/asset-registry/conversions.json",
                "tools/asset-registry/statuses.json",
            })
            for path, payload in before.items():
                self.assertEqual(after[path], payload, path)
        finally:
            temporary.cleanup()

    def test_no_forbidden_imports_or_rendering(self):
        source = (ROOT / "tools" / "asset-registry"
                  / "convert_unit.py").read_text(encoding="utf-8")
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
