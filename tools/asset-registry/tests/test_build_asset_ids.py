import contextlib
import hashlib
import io
import json
import re
import sys
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "asset-registry"))

import build_asset_ids as builder
import build_registry as source

COMMITTED = ROOT / "tools" / "asset-registry" / "asset_ids.json"

PINNED_DISTINCT = {
    "images": 607,
    "item_sprites": 872,
    "magic_sprites": 10,
    "sounds": 138,
}
PINNED_REFERENCES = {
    "images": 607,
    "item_sprites": 917,
    "magic_sprites": 10,
    "sounds": 139,
}
PINNED_RESOLVED = {
    "images": 525,
    "item_sprites": 907,
    "magic_sprites": 10,
    "sounds": 139,
}
PINNED_BY_KIND = {
    "images": {"passthrough": 516, "extracted": 9, "ambiguous": 50,
               "missing_source": 32},
    "item_sprites": {"converted": 2, "extracted": 857, "pending": 3,
                     "missing_source": 10},
    "magic_sprites": {"extracted": 6, "pending": 4},
    "sounds": {"passthrough": 138},
}
PINNED_PACKAGES = {
    "0001_house_1_m": "assets/converted/buildings/0001_house_1_m",
    "10033_wild_elephant": "assets/converted/units/10033_wild_elephant",
}


def run_main(argv):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = builder.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def input_paths():
    """Every input file the builder consumes (extraction included)."""
    return [builder.REGISTRY_FILE, builder.COVERAGE_FILE,
            builder.CONVERSIONS_FILE, builder.IMAGE_EXTRACTION_FILE,
            *(tuple(source.ITEM_FILES) + (source.MAGICS_FILE,
                                          source.SOUNDS_FILE,
                                          source.IMAGES_FILE))]


def make_input_root():
    """Temp repo root with the four manifests and the six normalized files.

    image_extraction.json (37 MB) is intentionally omitted: the builder
    loads it lazily, after reconciliation, so failure cases stay fast and
    prove that ordering.
    """
    temporary = tempfile.TemporaryDirectory()
    work = Path(temporary.name) / "repo"
    for relative in input_paths():
        if relative == builder.IMAGE_EXTRACTION_FILE:
            continue
        target = work / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    return temporary, work


def files_under(root):
    return sorted(str(path.relative_to(root)).replace("\\", "/")
                  for path in Path(root).rglob("*") if path.is_file())


_REAL_BUILD = None


def real_build():
    """One shared real-tree build writing to a temp out-root."""
    global _REAL_BUILD
    if _REAL_BUILD is None:
        temporary = tempfile.TemporaryDirectory()
        out = Path(temporary.name) / "out"
        out.mkdir(parents=True)
        code, stdout, _ = run_main(["--repo-root", str(ROOT),
                                    "--out-root", str(out)])
        assert code == 0, stdout
        _REAL_BUILD = (temporary, out)
    return _REAL_BUILD[1]


def built_payload():
    return read_json(real_build() / builder.OUTPUT_FILE)


class RebuildDeterminismTests(unittest.TestCase):
    def test_rebuild_matches_committed_bytes(self):
        rebuilt = (real_build() / builder.OUTPUT_FILE).read_bytes()
        self.assertEqual(rebuilt, COMMITTED.read_bytes())

    def test_rerun_is_byte_identical(self):
        first_out = real_build() / builder.OUTPUT_FILE
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        out = Path(temporary.name) / "second"
        out.mkdir(parents=True)
        code, stdout, _ = run_main(["--repo-root", str(ROOT),
                                    "--out-root", str(out)])
        self.assertEqual(code, 0, stdout)
        self.assertEqual((out / builder.OUTPUT_FILE).read_bytes(),
                         first_out.read_bytes())

    def test_identity_fields(self):
        payload = built_payload()
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["policy"], "asset-id-registry-v1")
        self.assertEqual(payload["result"], "success")
        self.assertEqual([kind["kind"] for kind in payload["kinds"]],
                         list(builder.KIND_ORDER))
        records = [record["file"] for record in payload["inputs"]]
        self.assertEqual(records, sorted(records))
        self.assertEqual(len(records), 10)


class EvidenceReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = built_payload()
        cls.coverage = read_json(ROOT / builder.COVERAGE_FILE)
        cls.by_kind = {kind["kind"]: kind for kind in cls.payload["kinds"]}
        cls.conversions = read_json(ROOT / builder.CONVERSIONS_FILE)

    def entries(self, kind):
        return self.by_kind[kind]["entries"]

    def test_counts_reconcile_with_coverage(self):
        counts = self.payload["counts"]
        for kind, domain in self.coverage["domains"].items():
            self.assertEqual(counts["references"][kind],
                             domain["references"], kind)
            self.assertEqual(counts["distinct"][kind],
                             domain["distinct_references"], kind)
            self.assertEqual(counts["resolved_references"][kind],
                             domain["resolved"], kind)
        images = self.coverage["domains"]["images"]
        self.assertEqual(images["basename_single"], 525)
        self.assertEqual(images["basename_collision"], 50)

    def test_missing_lists_equal_coverage_missing_lists(self):
        counts = self.payload["counts"]
        for kind in builder.KIND_ORDER:
            missing = sorted(entry["ref"] for entry in self.entries(kind)
                             if entry["status"] == "missing_source")
            self.assertEqual(missing, self.coverage["domains"][kind]["missing"],
                             kind)
        self.assertEqual(counts["by_kind"]["images"]["missing_source"], 32)
        self.assertEqual(counts["by_kind"]["item_sprites"]["missing_source"],
                         10)
        self.assertEqual(counts["by_kind"]["magic_sprites"].get(
            "missing_source", 0), 0)
        self.assertEqual(counts["by_kind"]["sounds"].get(
            "missing_source", 0), 0)

    def test_converted_entries_equal_conversion_packages(self):
        packages = {package["legacy_id"]: package["directory"]
                    for package in self.conversions["packages"]}
        self.assertEqual(packages, PINNED_PACKAGES)
        converted = {entry["ref"]: entry["runtime"]
                     for entry in self.entries("item_sprites")
                     if entry["status"] == "converted"}
        self.assertEqual(converted, packages)
        for runtime in converted.values():
            self.assertTrue((ROOT / runtime).is_dir(), runtime)

    def test_extracted_entries_derive_from_extraction_manifest(self):
        extraction = read_json(ROOT / builder.IMAGE_EXTRACTION_FILE)
        dirs_by_source = {}
        for record in extraction["bitmaps"]:
            directories = {output["file"].rsplit("/", 1)[0]
                           for output in record["outputs"]}
            dirs_by_source.setdefault(record["source"], set())
            dirs_by_source[record["source"]] |= directories
        checked = 0
        for kind in builder.KIND_ORDER:
            for entry in self.entries(kind):
                if entry["status"] != "extracted":
                    continue
                checked += 1
                runtime = entry["runtime"]
                self.assertTrue(
                    runtime.startswith(builder.EXTRACTED_PREFIX), runtime)
                self.assertEqual(dirs_by_source.get(entry["source"]), {runtime},
                                 entry["ref"])
                self.assertNotIn(entry["ref"], PINNED_PACKAGES)
        self.assertEqual(checked, counts_extracted(self.payload))

    def test_vocabulary_and_runtime_contract(self):
        for kind in builder.KIND_ORDER:
            seen = []
            for entry in self.entries(kind):
                self.assertIn(entry["status"], builder.STATUSES,
                              "%s/%s" % (kind, entry["ref"]))
                seen.append(entry["ref"])
                if entry["status"] in ("converted", "extracted",
                                       "passthrough"):
                    self.assertTrue(entry["runtime"], entry)
                    self.assertTrue(entry["source"], entry)
                    self.assertEqual(len(entry["source_sha256"]), 64, entry)
                else:
                    self.assertIsNone(entry["runtime"], entry)
                if entry["status"] == "ambiguous":
                    self.assertTrue(entry["candidates"], entry)
                    self.assertEqual(entry["candidates"],
                                     sorted(entry["candidates"]), entry)
                    self.assertIsNone(entry["source"], entry)
            self.assertEqual(seen, sorted(seen), kind)
            self.assertEqual(len(seen), len(set(seen)), kind)

    def test_reference_counts_sum_to_coverage_references(self):
        for kind in builder.KIND_ORDER:
            total = sum(entry["reference_count"]
                        for entry in self.entries(kind))
            self.assertEqual(total, PINNED_REFERENCES[kind], kind)

    def test_pinned_status_counts(self):
        counts = self.payload["counts"]
        self.assertEqual(counts["distinct"], PINNED_DISTINCT)
        self.assertEqual(counts["references"], PINNED_REFERENCES)
        self.assertEqual(counts["resolved_references"], PINNED_RESOLVED)
        self.assertEqual(counts["by_kind"], PINNED_BY_KIND)
        self.assertEqual(counts["entries"], 1627)
        self.assertEqual(counts["by_status"], {
            "ambiguous": 50,
            "converted": 2,
            "extracted": 872,
            "missing_source": 42,
            "passthrough": 654,
            "pending": 7,
        })
        for kind in builder.KIND_ORDER:
            self.assertEqual(sum(counts["by_kind"][kind].values()),
                             PINNED_DISTINCT[kind], kind)
        self.assertEqual(sum(counts["by_status"].values()),
                         counts["entries"])

    def test_inputs_records_match_committed_files(self):
        for record in self.payload["inputs"]:
            path = ROOT / record["file"]
            self.assertTrue(path.is_file(), record["file"])
            self.assertEqual(record["bytes"], path.stat().st_size,
                             record["file"])
            self.assertEqual(record["sha256"], file_sha256(path),
                             record["file"])

    def test_rules_match_coverage_rules(self):
        for kind in builder.KIND_ORDER:
            self.assertEqual(self.by_kind[kind]["rule"],
                             self.coverage["domains"][kind]["rule"], kind)


def counts_extracted(payload):
    return payload["counts"]["by_status"]["extracted"]


class PreservationTests(unittest.TestCase):
    def test_sources_unchanged_by_build(self):
        before = {str(relative): file_sha256(ROOT / relative)
                  for relative in input_paths()}
        committed_before = file_sha256(COMMITTED)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        out = Path(temporary.name) / "out"
        out.mkdir(parents=True)
        code, stdout, _ = run_main(["--repo-root", str(ROOT),
                                    "--out-root", str(out)])
        self.assertEqual(code, 0, stdout)
        for relative, digest in before.items():
            self.assertEqual(file_sha256(ROOT / relative), digest, relative)
        self.assertEqual(file_sha256(COMMITTED), committed_before)

    def test_output_file_is_the_only_write(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        out = Path(temporary.name) / "out"
        out.mkdir(parents=True)
        code, stdout, _ = run_main(["--repo-root", str(ROOT),
                                    "--out-root", str(out)])
        self.assertEqual(code, 0, stdout)
        self.assertEqual(files_under(out),
                         ["tools/asset-registry/asset_ids.json"])


class FailureTests(unittest.TestCase):
    def test_tampered_coverage_fails_without_writing(self):
        temporary, work = make_input_root()
        self.addCleanup(temporary.cleanup)
        coverage_path = work / builder.COVERAGE_FILE
        coverage = read_json(coverage_path)
        coverage["domains"]["images"]["resolved"] += 1
        coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
        out = work / "out"
        out.mkdir()
        code, stdout, _ = run_main(["--repo-root", str(work),
                                    "--out-root", str(out)])
        self.assertEqual(code, 1)
        self.assertIn("coverage mismatch", stdout)
        self.assertIn("validation-failed", stdout)
        self.assertEqual(files_under(out), [])

    def test_missing_conversions_exits_2_without_writing(self):
        temporary, work = make_input_root()
        self.addCleanup(temporary.cleanup)
        (work / builder.CONVERSIONS_FILE).unlink()
        out = work / "out"
        out.mkdir()
        code, _, stderr = run_main(["--repo-root", str(work),
                                    "--out-root", str(out)])
        self.assertEqual(code, 2)
        self.assertIn("file missing", stderr)
        self.assertEqual(files_under(out), [])

    def test_tampered_normalized_reference_exits_2_without_writing(self):
        temporary, work = make_input_root()
        self.addCleanup(temporary.cleanup)
        sounds_path = work / source.SOUNDS_FILE
        sounds_path.write_text("{broken", encoding="utf-8")
        out = work / "out"
        out.mkdir()
        code, _, stderr = run_main(["--repo-root", str(work),
                                    "--out-root", str(out)])
        self.assertEqual(code, 2)
        self.assertIn("not valid json", stderr)
        self.assertEqual(files_under(out), [])


class ContainmentTests(unittest.TestCase):
    def test_no_forbidden_imports_or_subprocess(self):
        source_text = (ROOT / "tools" / "asset-registry"
                       / "build_asset_ids.py").read_text(encoding="utf-8")
        for line in source_text.splitlines():
            match = re.match(r"\s*(import|from)\s+(\S+)", line)
            if not match:
                continue
            module = match.group(2).split(".")[0]
            self.assertNotIn(module, ("get_game_config", "jsonpatch", "flask",
                                      "server", "command", "engine",
                                      "requests", "subprocess", "socket",
                                      "urllib", "webbrowser", "http",
                                      "shutil", "zipfile", "tarfile"),
                             "forbidden import: " + line)
        self.assertNotIn("Popen", source_text)
        self.assertNotIn("os.system", source_text)

    def test_committed_registry_is_readable_by_the_client_contract(self):
        # The Godot ContentRegistry validates identity + kinds + vocabulary;
        # mirror that contract here so a drift fails on the Python side too.
        payload = read_json(COMMITTED)
        self.assertEqual(payload["schema_version"],
                         builder.SCHEMA_VERSION)
        self.assertEqual(payload["policy"], builder.POLICY)
        self.assertEqual(payload["result"], "success")
        kinds = {kind["kind"]: kind["entries"] for kind in payload["kinds"]}
        self.assertEqual(sorted(kinds), sorted(builder.KIND_ORDER))
        for kind, entries in kinds.items():
            for entry in entries:
                self.assertIsInstance(entry["ref"], str, kind)
                self.assertIn(entry["status"], builder.STATUSES,
                              "%s/%s" % (kind, entry["ref"]))


if __name__ == "__main__":
    unittest.main()
