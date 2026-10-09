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
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "asset-registry"))

import build_registry as builder

EXPECTED_MISSING_SPRITES = sorted([
    "0137_spy_academy_m",
    "10000_chained_bonus_giant_walker",
    "10027_prision",
    "10034_chained_hercules_mech",
    "10048_cross_dc",
    "1011_bad_girl_m",
    "982_chained_red_spinner",
    "casachina",
    "treasure",
    "vacaPerdida",
])


def snapshot(root):
    return {str(path.relative_to(root)).replace("\\", "/"):
            ("directory" if path.is_dir() else path.read_bytes())
            for path in Path(root).rglob("*")}


def run_main(argv):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = builder.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def write_bytes(work, relative, payload):
    target = work / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return target


def make_fixture_tree():
    """Small synthetic repo root exercising includes, cases, exclusions."""
    temporary = tempfile.TemporaryDirectory()
    work = Path(temporary.name) / "repo"
    write_bytes(work, "assets/sprites/house_a.swf", b"SWFDATA-a")
    write_bytes(work, "assets/sprites/house_b.SWF", b"SWFDATA-b")
    write_bytes(work, "assets/sounds/hit.mp3", b"MP3DATA")
    write_bytes(work, "assets/magic/house_a.swf", b"MAGICDATA")
    write_bytes(work, "assets/images/logo.PNG", b"PNGDATA")
    write_bytes(work, "assets/images/photo.JPG", b"JPGDATA")
    write_bytes(work, "templates/slide.jpg", b"TEMPLATEDATA")
    write_bytes(work, "docs/notes.md", b"not an asset")
    write_bytes(work, "saves/player.json", b"excluded")
    write_bytes(work, "temp/work.swf", b"excluded")
    write_bytes(work, "new_assets/draft.png", b"excluded")
    write_bytes(work, "build/bundle/out.swf", b"excluded")
    write_bytes(work, "build/work/tmp.mp3", b"excluded")
    write_bytes(work, "assets/converted/sounds/9.mp3", b"generated")
    write_bytes(work, "apps/client-godot/evidence/first-render/first-render.png",
                b"modern-client-output")
    normalized = work / "packages" / "game-content" / "normalized"
    normalized.mkdir(parents=True)
    (normalized / "units.json").write_text(json.dumps([
        {"legacy_id": "u1", "img_name": "house_a"}]), encoding="utf-8")
    (normalized / "specials.json").write_text(json.dumps([
        {"legacy_id": "s1", "img_name": "house_b"}]), encoding="utf-8")
    (normalized / "buildings.json").write_text(json.dumps([
        {"legacy_id": "1", "img_name": "house_a,house_b"},
    ]), encoding="utf-8")
    (normalized / "magics.json").write_text(json.dumps([
        {"legacy_id": "1", "img_name": "house_a"},
    ]), encoding="utf-8")
    (normalized / "sounds.json").write_text(json.dumps([
        {"legacy_id": "1", "file": "hit"},
    ]), encoding="utf-8")
    (normalized / "images.json").write_text(json.dumps([
        {"legacy_id": "/x/logo.PNG", "path": "/x/logo.PNG"},
        {"legacy_id": "gone.jpg", "path": "gone.jpg"},
    ]), encoding="utf-8")
    schemas = work / "tools" / "asset-registry" / "schemas"
    schemas.mkdir(parents=True)
    for name in ("registry.schema.json", "registry_entry.schema.json",
                 "coverage.schema.json"):
        shutil.copy2(ROOT / "tools" / "asset-registry" / "schemas" / name,
                     schemas / name)
    return temporary, work


def read_out_json(out, relative):
    return json.loads((out / relative).read_text(encoding="utf-8"))


_REAL_BUILD = None


def real_build():
    """One shared real-tree build writing to a temp out-root (read-only root)."""
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


class FixtureEnumerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary, cls.work = make_fixture_tree()
        cls.addClassCleanup(cls.temporary.cleanup)
        code, stdout, _ = run_main(["--repo-root", str(cls.work),
                                    "--out-root", str(cls.work)])
        assert code == 0, stdout
        cls.registry = read_out_json(cls.work, "tools/asset-registry/registry.json")
        cls.coverage = read_out_json(cls.work, "tools/asset-registry/coverage.json")

    def test_includes_asset_extensions_case_insensitive(self):
        paths = [entry["path"] for entry in self.registry["entries"]]
        self.assertIn("assets/sprites/house_a.swf", paths)
        self.assertIn("assets/sprites/house_b.SWF", paths)
        self.assertIn("assets/sounds/hit.mp3", paths)
        self.assertIn("assets/images/logo.PNG", paths)
        self.assertIn("templates/slide.jpg", paths)
        self.assertNotIn("docs/notes.md", paths)

    def test_exclusions_contribute_nothing(self):
        paths = [entry["path"] for entry in self.registry["entries"]]
        for excluded in ("saves/player.json", "temp/work.swf",
                         "new_assets/draft.png", "build/bundle/out.swf",
                         "build/work/tmp.mp3", "assets/converted/sounds/9.mp3",
                         "apps/client-godot/evidence/first-render/first-render.png"):
            self.assertNotIn(excluded, paths)
        self.assertEqual(len(paths), 7)

    def test_entry_fields_and_digest(self):
        by_path = {entry["path"]: entry for entry in self.registry["entries"]}
        entry = by_path["assets/sprites/house_a.swf"]
        self.assertEqual(entry["size"], len(b"SWFDATA-a"))
        self.assertEqual(entry["sha256"], hashlib.sha256(b"SWFDATA-a").hexdigest())
        self.assertEqual(entry["extension"], ".swf")
        self.assertEqual(entry["directory_class"], "assets")
        self.assertEqual(entry["status"], "registered")
        self.assertEqual(by_path["assets/sprites/house_b.SWF"]["extension"], ".swf")

    def test_sorted_posix_order(self):
        paths = [entry["path"] for entry in self.registry["entries"]]
        self.assertEqual(paths, sorted(paths))
        self.assertTrue(all("\\" not in path for path in paths))

    def test_fixture_joins(self):
        sprites = self.coverage["domains"]["item_sprites"]
        self.assertEqual(sprites["references"], 4)
        # Joins are case-sensitive (Godot/Linux paths are too): house_b.SWF
        # on disk does not satisfy the house_b reference.
        self.assertEqual(sprites["resolved"], 2)
        self.assertEqual(sprites["missing"], ["house_b"])
        self.assertEqual(self.coverage["domains"]["magic_sprites"]["resolved"], 1)
        self.assertEqual(self.coverage["domains"]["sounds"]["resolved"], 1)
        images = self.coverage["domains"]["images"]
        self.assertEqual(images["resolved"], 1)
        self.assertEqual(images["missing"], ["gone.jpg"])
        self.assertIn("assets", self.coverage["unreferenced"])
        self.assertIn("templates", self.coverage["unreferenced"])


class RealTreeJoinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = real_build()
        cls.registry = read_out_json(cls.out, "tools/asset-registry/registry.json")
        cls.coverage = read_out_json(cls.out, "tools/asset-registry/coverage.json")

    def test_corpus_totals_match_measurements(self):
        counts = self.registry["counts"]
        self.assertEqual(counts["files"], 3215)
        self.assertEqual(counts["by_extension"][".swf"], 1176)
        self.assertEqual(counts["by_extension"][".jpg"], 1756)
        self.assertEqual(counts["by_extension"][".png"], 143)
        self.assertEqual(counts["by_extension"][".mp3"], 140)
        self.assertEqual(counts["by_directory_class"]["assets"], 3199)
        self.assertEqual(counts["by_directory_class"]["templates"], 16)

    def test_item_sprite_join_with_ten_missing(self):
        sprites = self.coverage["domains"]["item_sprites"]
        self.assertEqual(sprites["references"], 917)
        self.assertEqual(sprites["resolved"], 907)
        self.assertEqual(sprites["missing"], EXPECTED_MISSING_SPRITES)

    def test_magic_and_sound_joins_complete(self):
        magic = self.coverage["domains"]["magic_sprites"]
        self.assertEqual(magic["references"], 10)
        self.assertEqual(magic["resolved"], 10)
        self.assertEqual(magic["missing"], [])
        sounds = self.coverage["domains"]["sounds"]
        self.assertEqual(sounds["references"], 139)
        self.assertEqual(sounds["resolved"], 139)
        self.assertEqual(sounds["missing"], [])

    def test_images_path_first_tiers(self):
        images = self.coverage["domains"]["images"]
        self.assertEqual(images["references"], 607)
        self.assertEqual(images["path_resolved"], 573)
        self.assertEqual(images["fallback_resolved"], 2)
        self.assertEqual(images["fallback_ambiguous"], 0)
        self.assertEqual(images["resolved"], 575)
        self.assertEqual(len(images["missing"]), 32)
        self.assertEqual(images["path_resolved"] + images["fallback_resolved"]
                         + images["fallback_ambiguous"]
                         + len(images["missing"]),
                         images["references"])

    def test_the_fallback_tier_names_its_two_members(self):
        # Task 1.3: the fallback is recorded by name, not only as a count.
        images = self.coverage["domains"]["images"]
        self.assertEqual(images["fallback_resolved_refs"], [
            "/chapters/simple/arachnids_old.jpg",
            "/chapters/simple/orcs_old.jpg",
        ])
        self.assertEqual(len(images["fallback_resolved_refs"]),
                         images["fallback_resolved"])
        self.assertEqual(images["fallback_ambiguous_refs"], [])
        self.assertEqual(len(images["fallback_ambiguous_refs"]),
                         images["fallback_ambiguous"])

    def test_no_image_reference_is_reported_as_a_collision(self):
        # Task 1.4: the collision tier the old rule needed is empty and the
        # field is gone, so no reference can be reported as one.
        images = self.coverage["domains"]["images"]
        self.assertNotIn("basename_collision", images)
        self.assertNotIn("basename_single", images)
        self.assertEqual(images["fallback_ambiguous"], 0)

    def test_the_thirty_two_refusals_are_the_absent_files(self):
        # Task 1.4: the 32 stay listed and none resolved.
        images = self.coverage["domains"]["images"]
        self.assertEqual(len(images["missing"]), 32)
        self.assertEqual(images["missing"], sorted(set(images["missing"])))
        registry_paths = {entry["path"]
                          for entry in self.registry["entries"]}
        for ref in images["missing"]:
            joined = builder.IMAGE_WEB_ROOT + "/" + ref.lstrip("/")
            self.assertNotIn(joined, registry_paths, ref)

    def test_the_recorded_rule_names_the_web_root_and_the_fallback(self):
        # Task 1.2: the recorded evidence describes the order performed.
        rule = self.coverage["domains"]["images"]["rule"]
        self.assertIn(builder.IMAGE_WEB_ROOT, rule)
        self.assertIn("basename fallback", rule)
        self.assertEqual(rule, builder.IMAGE_RULE)

    def test_the_join_is_a_bijection_onto_the_web_root_corpus(self):
        # Task 1.5, corrected: the bijection holds over the path-resolved
        # tier, not over all 575 identified references. See design.md
        # "Corrections found during Apply", C1.
        tiers = self.real_tiers()
        files = tiers["files"]

        # The path-resolved tier is exactly a bijection: 573 references,
        # 573 distinct corpus files, and that set is every corpus file
        # under the web root -- so nothing there is left unreferenced.
        path_files = [files[ref] for ref in tiers["path_resolved"]]
        self.assertEqual(len(path_files), 573)
        self.assertEqual(len(set(path_files)), 573)
        under_root = {entry["path"] for entry in self.registry["entries"]
                      if entry["path"].startswith(
                          builder.IMAGE_WEB_ROOT + "/")}
        self.assertEqual(len(under_root), 573)
        self.assertEqual(set(path_files), under_root)

        # All 575 identified references name 573 files, and the only two
        # shared targets are the mis-pathed fallback references aliasing
        # their chapters2 counterparts.
        self.assertEqual(len(files), 575)
        targets = {}
        for ref, path in files.items():
            targets.setdefault(path, []).append(ref)
        shared = {path: refs for path, refs in targets.items() if len(refs) > 1}
        self.assertEqual(len(shared), 2)
        self.assertEqual(sorted(sorted(refs) for refs in shared.values()), [
            ["/chapters/simple/arachnids_old.jpg",
             "/chapters2/simple/arachnids_old.jpg"],
            ["/chapters/simple/orcs_old.jpg",
             "/chapters2/simple/orcs_old.jpg"],
        ])
        for refs in shared.values():
            fallback = [ref for ref in refs
                        if ref in tiers["fallback_resolved"]]
            self.assertEqual(len(fallback), 1, refs)
        # Every identified file lies under the web root: nothing is
        # resolved to a file outside the corpus the rule claims to join.
        self.assertEqual(set(files.values()) - under_root, set())

    def test_the_bijection_assertion_is_not_tautological(self):
        # Task 1.5, second half: revert the join to the basename-only rule
        # and confirm the bijection assertion above actually fails. Without
        # this, "the assertion passes" could mean "the assertion cannot fail".
        tiers = self.basename_only_tiers()
        under_root = {entry["path"] for entry in self.registry["entries"]
                      if entry["path"].startswith(builder.IMAGE_WEB_ROOT + "/")}
        # The old rule leaves 50 references with no file at all, so it
        # cannot satisfy either half of the bijection assertion.
        self.assertEqual(len(tiers["files"]), 525)
        self.assertEqual(len(set(tiers["files"].values())), 523)
        self.assertNotEqual(set(tiers["files"].values()), under_root)
        self.assertEqual(len(tiers["fallback_ambiguous"]), 50)

    def real_tiers(self):
        """Re-derive the committed tiers from the committed inputs."""
        return self.join_tiers(builder.join_image_refs)

    def basename_only_tiers(self):
        """The previous rule, reimplemented here as the negative control."""
        def basename_only(refs, registry_paths, basenames):
            tiers = {"path_resolved": [], "fallback_resolved": [],
                     "fallback_ambiguous": [], "missing": [], "files": {}}
            for ref in refs:
                candidates = basenames.get(ref.rsplit("/", 1)[-1], [])
                if len(candidates) == 1:
                    tiers["fallback_resolved"].append(ref)
                    tiers["files"][ref] = candidates[0]
                elif candidates:
                    tiers["fallback_ambiguous"].append(ref)
                else:
                    tiers["missing"].append(ref)
            return tiers
        return self.join_tiers(basename_only)

    def join_tiers(self, join):
        registry_paths = {entry["path"]
                          for entry in self.registry["entries"]}
        basenames = {}
        for path in registry_paths:
            basenames.setdefault(path.rsplit("/", 1)[-1], []).append(path)
        refs = builder.extract_field_refs(ROOT, builder.IMAGES_FILE, "path")
        return join(refs, registry_paths, basenames)

    def test_unreferenced_counts_sane(self):
        total_unreferenced = sum(self.coverage["unreferenced"].values())
        self.assertGreater(total_unreferenced, 0)
        self.assertLessEqual(total_unreferenced, self.registry["counts"]["files"])

    def test_registry_manifest_grade(self):
        self.assertEqual(self.registry["schema_version"], 1)
        self.assertEqual(self.registry["policy"], "asset-registry-v1")
        self.assertEqual(self.registry["result"], "success")
        self.assertEqual(self.coverage["corpus"]["files"],
                         self.registry["counts"]["files"])


class ValidationFailureTests(unittest.TestCase):
    def setUp(self):
        self.temporary, self.work = make_fixture_tree()
        self.addCleanup(self.temporary.cleanup)

    def build(self):
        return run_main(["--repo-root", str(self.work),
                         "--out-root", str(self.work)])

    def test_corrupt_normalized_ref_exit_2(self):
        (self.work / "packages" / "game-content" / "normalized"
         / "sounds.json").write_text("{broken", encoding="utf-8")
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("not valid json", stderr)

    def test_missing_ref_file_exit_2(self):
        (self.work / "packages" / "game-content" / "normalized"
         / "magics.json").unlink()
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("file missing", stderr)

    def test_missing_img_name_exit_2(self):
        (self.work / "packages" / "game-content" / "normalized"
         / "buildings.json").write_text(json.dumps([{"legacy_id": "1"}]),
                                        encoding="utf-8")
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("img_name", stderr)

    def test_failure_writes_nothing(self):
        before = {path for path in snapshot(self.work)
                  if snapshot(self.work)[path] != "directory"}
        (self.work / "packages" / "game-content" / "normalized"
         / "sounds.json").write_text("{broken", encoding="utf-8")
        code, _, _ = self.build()
        self.assertEqual(code, 2)
        after = {path for path in snapshot(self.work)
                 if snapshot(self.work)[path] != "directory"}
        self.assertEqual(after, before)

    def test_determinism_byte_identical_reruns(self):
        code, _, _ = self.build()
        self.assertEqual(code, 0)
        first = {name: (self.work / name).read_bytes() for name in (
            "tools/asset-registry/registry.json",
            "tools/asset-registry/coverage.json")}
        code, _, _ = self.build()
        self.assertEqual(code, 0)
        for name, payload in first.items():
            self.assertEqual((self.work / name).read_bytes(), payload, name)


class TraceabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry_schema = json.loads(
            (ROOT / builder.REGISTRY_SCHEMA_FILE).read_text(encoding="utf-8"))
        cls.entry_schema = json.loads(
            (ROOT / builder.ENTRY_SCHEMA_FILE).read_text(encoding="utf-8"))
        cls.coverage_schema = json.loads(
            (ROOT / builder.COVERAGE_SCHEMA_FILE).read_text(encoding="utf-8"))
        out = real_build()
        cls.registry = read_out_json(out, "tools/asset-registry/registry.json")
        cls.coverage = read_out_json(out, "tools/asset-registry/coverage.json")
        cls.entry = cls.registry["entries"][0]

    def test_every_required_field_is_enforced(self):
        for schema, item, label in (
                (self.registry_schema, self.registry, "registry"),
                (self.entry_schema, self.entry, "registry_entry"),
                (self.coverage_schema, self.coverage, "coverage")):
            for field in schema["required"]:
                mutated = dict(item)
                del mutated[field]
                problems = builder.validate_against_schema(
                    mutated, schema, label)
                self.assertTrue(
                    any("missing required field" in problem
                        and field in problem for problem in problems),
                    "no validator check for required field %s.%s"
                    % (label, field))

    def test_wrong_types_are_rejected(self):
        mutated = dict(self.entry)
        mutated["size"] = "10"
        self.assertTrue(builder.validate_against_schema(
            mutated, self.entry_schema, "registry_entry"))
        mutated = dict(self.entry)
        mutated["status"] = "converted"
        self.assertTrue(builder.validate_against_schema(
            mutated, self.entry_schema, "registry_entry"))
        mutated = dict(self.registry)
        mutated["schema_version"] = "1"
        self.assertTrue(builder.validate_against_schema(
            mutated, self.registry_schema, "registry"))

    def test_digest_format_enforced(self):
        problems = []
        builder.validate_digest("xyz", "probe", problems)
        self.assertTrue(problems)
        problems = []
        builder.validate_digest("A" * 64, "probe", problems)
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

    def test_fixture_reads_bounded_and_writes_exact(self):
        temporary, work = make_fixture_tree()
        try:
            code, _, _, opened, before = self.guarded_run(
                work, ["--repo-root", str(work), "--out-root", str(work)])
            self.assertEqual(code, 0)
            reads, writes = self.observed_sets(work, opened)
            self.assertEqual(writes, {
                "tools/asset-registry/registry.json",
                "tools/asset-registry/coverage.json",
            })
            self.assertEqual(reads, {
                "assets/sprites/house_a.swf",
                "assets/sprites/house_b.SWF",
                "assets/sounds/hit.mp3",
                "assets/magic/house_a.swf",
                "assets/images/logo.PNG",
                "assets/images/photo.JPG",
                "templates/slide.jpg",
                "packages/game-content/normalized/buildings.json",
                "packages/game-content/normalized/units.json",
                "packages/game-content/normalized/specials.json",
                "packages/game-content/normalized/magics.json",
                "packages/game-content/normalized/sounds.json",
                "packages/game-content/normalized/images.json",
                "tools/asset-registry/schemas/registry.schema.json",
                "tools/asset-registry/schemas/registry_entry.schema.json",
                "tools/asset-registry/schemas/coverage.schema.json",
            })
            after = snapshot(work)
            new_files = {path for path in set(after) - set(before)
                         if after[path] != "directory"}
            self.assertEqual(new_files, {
                "tools/asset-registry/registry.json",
                "tools/asset-registry/coverage.json",
            })
            for path, payload in before.items():
                if path in ("tools/asset-registry/registry.json",
                            "tools/asset-registry/coverage.json"):
                    continue
                self.assertEqual(after[path], payload, path)
        finally:
            temporary.cleanup()

    def test_no_forbidden_imports_or_subprocess(self):
        source = (ROOT / "tools" / "asset-registry"
                  / "build_registry.py").read_text(encoding="utf-8")
        for line in source.splitlines():
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
        self.assertNotIn("Popen", source)
        self.assertNotIn("os.system", source)


if __name__ == "__main__":
    unittest.main()
