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
sys.path.insert(0, str(ROOT / "packages" / "game-content" / "tools"))

import build_images as builder

EXPECTED_READS = frozenset([
    "config/main.json",
    "config/patch/patches.txt",
    "config/patch/atom_fusion_item.json",
    "config/patch/unit_patch.json",
    "config/patch/atom_fusion_items_data.json",
    "config/patch/atom_fusion_powerup.json",
    "config/patch/targets.json",
    "mods/mods.txt",
    "packages/game-content/schemas/image_asset.schema.json",
    "packages/game-content/manifest.json",
])

EXPECTED_WRITES = frozenset([
    "packages/game-content/normalized/images.json",
    "packages/game-content/manifest.json",
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


def make_work_tree():
    temporary = tempfile.TemporaryDirectory()
    work = Path(temporary.name) / "repo"
    shutil.copytree(ROOT / "config", work / "config")
    shutil.copytree(ROOT / "mods", work / "mods")
    (work / "packages" / "game-content" / "tools").mkdir(parents=True)
    shutil.copy2(ROOT / "packages" / "game-content" / "tools" / "build_images.py",
                 work / "packages" / "game-content" / "tools" / "build_images.py")
    (work / "packages" / "game-content" / "schemas").mkdir(parents=True)
    shutil.copy2(ROOT / "packages" / "game-content" / "schemas" / "image_asset.schema.json",
                 work / "packages" / "game-content" / "schemas" / "image_asset.schema.json")
    (work / "packages" / "game-content" / "normalized").mkdir(parents=True)
    shutil.copy2(ROOT / "packages" / "game-content" / "manifest.json",
                 work / "packages" / "game-content" / "manifest.json")
    return temporary, work


def read_work_json(work, relative):
    return json.loads((work / relative).read_text(encoding="utf-8"))


def write_work_json(work, relative, document):
    (work / relative).write_text(json.dumps(document), encoding="utf-8")


def load_work_images(work):
    return read_work_json(work, "config/main.json")["images"]


def save_work_images(work, entries):
    document = read_work_json(work, "config/main.json")
    document["images"] = entries
    write_work_json(work, "config/main.json", document)


class VerbatimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        layers = builder.load_all(str(ROOT))
        cls.layers = layers
        cls.first = builder.coerce_image("/chapters/chapter_1.jpg", "en",
                                         "image /chapters/chapter_1.jpg")

    def test_path_and_locale_verbatim(self):
        self.assertEqual(self.first["path"], "/chapters/chapter_1.jpg")
        self.assertEqual(self.first["locale"], "en")

    def test_rejects_non_en_locale(self):
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_image("/chapters/chapter_1.jpg", "fr", "mutated")

    def test_rejects_empty_path(self):
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_image("", "en", "mutated")

    def test_rejects_non_string_path(self):
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_image(5, "en", "mutated")


class ClassificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        layers = builder.load_all(str(ROOT))
        cls.layers = layers
        cls.images_section, cls.payloads = builder.build_package(
            str(ROOT), str(ROOT))

    def test_counts_match_verified_measurements(self):
        counts = self.images_section["counts"]
        self.assertEqual(counts["stored_images"], 607)
        self.assertEqual(counts["images"], 607)
        self.assertEqual(counts["extensions"],
                         {"jpg": 470, "png": 127, "swf": 10})
        self.assertEqual(counts["leading_slash"], 459)
        self.assertEqual(len(counts["swf_paths"]), 10)

    def test_all_locales_en(self):
        for value in self.layers["images"].values():
            self.assertEqual(value, "en")

    def test_no_patch_targets_images_content(self):
        self.assertEqual(self.images_section["inputs"]["images_patch_targets"],
                         "none")
        self.assertEqual(self.images_section["inputs"]["patch_order"],
                         ["atom_fusion_item", "unit_patch",
                          "atom_fusion_items_data", "atom_fusion_powerup",
                          "targets"])

    def test_envelope_fields_present(self):
        entries = json.loads(self.payloads[builder.IMAGES_FILE])
        for item in entries:
            for field in ("legacy_id", "kind", "source_file",
                          "source_layer", "content_version"):
                self.assertIn(field, item)
            self.assertEqual(item["kind"], "image_asset")
            self.assertEqual(item["source_layer"], "stored")
            self.assertEqual(item["source_file"], "config/main.json")
            self.assertEqual(item["legacy_id"], item["path"])
            self.assertEqual(item["locale"], "en")
            self.assertEqual(item["content_version"],
                             self.images_section["content_fingerprint"])

    def test_key_order_matches_stored_document(self):
        entries = json.loads(self.payloads[builder.IMAGES_FILE])
        self.assertEqual([item["legacy_id"] for item in entries],
                         list(self.layers["images"].keys()))


class ValidationFailureTests(unittest.TestCase):
    def setUp(self):
        self.temporary, self.work = make_work_tree()
        self.addCleanup(self.temporary.cleanup)

    def build(self):
        return run_main(["--repo-root", str(self.work),
                         "--out-root", str(self.work)])

    def test_clean_work_tree_build_exit_0(self):
        code, stdout, _ = self.build()
        self.assertEqual(code, 0)
        report = json.loads(stdout)
        self.assertEqual(report["result"], "success")
        self.assertEqual(report["counts"]["images"], 607)

    def test_non_en_locale_exit_1(self):
        entries = load_work_images(self.work)
        entries["/chapters/chapter_1.jpg"] = "fr"
        save_work_images(self.work, entries)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("locale drift", " ".join(json.loads(stdout)["problems"]))

    def test_duplicate_key_impossible_but_count_guarded(self):
        # JSON objects cannot hold duplicate keys; the builder still guards
        # the key set size explicitly.
        code, stdout, _ = self.build()
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["counts"]["images"], 607)

    def test_missing_schema_field_exit_2(self):
        schema = read_work_json(self.work,
                                "packages/game-content/schemas/image_asset.schema.json")
        del schema["properties"]["locale"]
        write_work_json(self.work,
                        "packages/game-content/schemas/image_asset.schema.json",
                        schema)
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("required not in properties", stderr)

    def test_failure_writes_nothing(self):
        before_manifest = (self.work / builder.MANIFEST_FILE).read_bytes()
        entries = load_work_images(self.work)
        entries["/chapters/chapter_1.jpg"] = "fr"
        save_work_images(self.work, entries)
        code, _, _ = self.build()
        self.assertEqual(code, 1)
        for name in EXPECTED_WRITES:
            if name == "packages/game-content/manifest.json":
                continue
            self.assertFalse((self.work / name).exists(), name)
        self.assertEqual((self.work / builder.MANIFEST_FILE).read_bytes(),
                         before_manifest)

    def test_images_patch_target_exit_2(self):
        patch = self.work / "config" / "patch" / "targets.json"
        operations = json.loads(patch.read_text(encoding="utf-8"))
        operations.append({"op": "add", "path": "/images/new", "value": "en"})
        patch.write_text(json.dumps(operations), encoding="utf-8")
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("images content", stderr)

    def test_active_mod_exit_2(self):
        mods = self.work / "mods" / "mods.txt"
        mods.write_text(mods.read_text(encoding="utf-8") + "\nno_hiring_needed\n",
                        encoding="utf-8")
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("active mods", stderr)

    def test_unparseable_content_exit_2(self):
        (self.work / "config" / "main.json").write_text("{broken",
                                                        encoding="utf-8")
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("not valid json", stderr)


class TraceabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _images_section, payloads = builder.build_package(str(ROOT), str(ROOT))
        cls.images_schema = json.loads(
            (ROOT / builder.IMAGES_SCHEMA_FILE).read_text(encoding="utf-8"))
        cls.entry = json.loads(payloads[builder.IMAGES_FILE])[0]

    def test_required_is_subset_of_properties(self):
        for field in self.images_schema["required"]:
            self.assertIn(field, self.images_schema["properties"],
                          "required not in properties: " + field)

    def test_every_required_field_is_enforced(self):
        for field in self.images_schema["required"]:
            mutated = dict(self.entry)
            del mutated[field]
            problems = builder.validate_against_schema(
                mutated, self.images_schema,
                "image_asset " + self.entry["legacy_id"])
            self.assertTrue(
                any("missing required field" in problem
                    and field in problem for problem in problems),
                "no validator check for required field image_asset.%s" % (field,))

    def test_wrong_types_are_rejected(self):
        cases = [("path", 5), ("locale", 5)]
        for field, bad in cases:
            mutated = dict(self.entry)
            mutated[field] = bad
            problems = builder.validate_against_schema(
                mutated, self.images_schema,
                "image_asset " + self.entry["legacy_id"])
            self.assertTrue(problems,
                            "no type check for image_asset.%s" % (field,))

    def test_locale_enum_enforced(self):
        mutated = dict(self.entry)
        mutated["locale"] = "fr"
        problems = builder.validate_against_schema(
            mutated, self.images_schema, "image_asset")
        self.assertTrue(any("enum mismatch" in problem for problem in problems))

    def test_kind_const_and_no_extra_properties(self):
        mutated = dict(self.entry)
        mutated["kind"] = "building"
        self.assertTrue(builder.validate_against_schema(
            mutated, self.images_schema, "image_asset"))
        mutated = dict(self.entry)
        mutated["invented_field"] = 1
        problems = builder.validate_against_schema(
            mutated, self.images_schema, "image_asset")
        self.assertTrue(any("additional property" in problem
                            for problem in problems))


class RoundTripTests(unittest.TestCase):
    def test_round_trip_clean_on_real_content(self):
        layers = builder.load_all(str(ROOT))
        _images_section, payloads = builder.build_package(str(ROOT), str(ROOT))
        entries = json.loads(payloads[builder.IMAGES_FILE])
        problems = builder.check_round_trip(entries,
                                            list(layers["images"].keys()),
                                            layers["images"])
        self.assertEqual(problems, [])

    def test_repeated_work_tree_builds_byte_identical(self):
        temporary, work = make_work_tree()
        self.addCleanup(temporary.cleanup)
        code, _, _ = run_main(["--repo-root", str(work),
                               "--out-root", str(work)])
        self.assertEqual(code, 0)
        first = {name: (work / name).read_bytes() for name in EXPECTED_WRITES}
        code, _, _ = run_main(["--repo-root", str(work),
                               "--out-root", str(work)])
        self.assertEqual(code, 0)
        for name, payload in first.items():
            self.assertEqual((work / name).read_bytes(), payload, name)


class ManifestTests(unittest.TestCase):
    def test_manifest_matches_produced_output(self):
        temporary, work = make_work_tree()
        try:
            code, _, _ = run_main(["--repo-root", str(work),
                                   "--out-root", str(work)])
            self.assertEqual(code, 0)
            manifest = read_work_json(work, "packages/game-content/manifest.json")
            self.assertIn("images", manifest)
            images_section = manifest["images"]
            self.assertEqual(images_section["result"], "success")
            self.assertEqual(images_section["policy"], builder.POLICY)
            self.assertEqual(images_section["coercion_ruleset"],
                             builder.COERCION_RULESET_VERSION)
            counts = images_section["counts"]
            entries = read_work_json(
                work, "packages/game-content/normalized/images.json")
            self.assertEqual(len(entries), counts["images"])
            self.assertEqual(counts["stored_images"], 607)
            self.assertEqual(counts["extensions"],
                             {"jpg": 470, "png": 127, "swf": 10})
            self.assertEqual(images_section["content_fingerprint"],
                             builder.fingerprint_inputs(
                                 builder.load_all(str(work))))
            by_file = {entry["file"]: entry
                       for entry in images_section["outputs"]}
            self.assertEqual(set(by_file),
                             set(EXPECTED_WRITES)
                             - {"packages/game-content/manifest.json"})
            data = (work / "packages/game-content/normalized/images.json").read_bytes()
            self.assertEqual(by_file["packages/game-content/normalized/images.json"]["bytes"],
                             len(data))
            self.assertEqual(by_file["packages/game-content/normalized/images.json"]["sha256"],
                             hashlib.sha256(data).hexdigest())
            self.assertTrue(images_section["notes"])
            # Prior keys survive the images merge untouched.
            self.assertEqual(manifest["policy"], "items-normalization-v1")
            self.assertEqual(manifest["counts"]["loaded_items"], 900)
            self.assertEqual(manifest["offers"]["policy"],
                             "offers-normalization-v1")
            self.assertEqual(manifest["offers"]["counts"]["offers"], 44)
        finally:
            temporary.cleanup()


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
        # pathlib.Path.read_bytes resolves to io.open, not builtins.open,
        # so both entry points are guarded.
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

    def test_success_reads_only_expected_and_inputs_unchanged(self):
        temporary, work = make_work_tree()
        try:
            code, _, _, opened, before = self.guarded_run(
                work, ["--repo-root", str(work), "--out-root", str(work)])
            self.assertEqual(code, 0)
            reads, writes = self.observed_sets(work, opened)
            self.assertEqual(reads, EXPECTED_READS)
            self.assertEqual(writes, EXPECTED_WRITES)
            after = snapshot(work)
            new_files = {path for path in set(after) - set(before)
                         if after[path] != "directory"}
            self.assertEqual(new_files,
                             {"packages/game-content/normalized/images.json"})
            for path, payload in before.items():
                if path == "packages/game-content/manifest.json":
                    continue
                self.assertEqual(after[path], payload, path)
        finally:
            temporary.cleanup()

    def test_failure_writes_nothing_and_inputs_unchanged(self):
        temporary, work = make_work_tree()
        try:
            entries = load_work_images(work)
            entries["/chapters/chapter_1.jpg"] = "fr"
            save_work_images(work, entries)
            code, _, _, opened, before = self.guarded_run(
                work, ["--repo-root", str(work), "--out-root", str(work)])
            self.assertEqual(code, 1)
            _reads, writes = self.observed_sets(work, opened)
            self.assertEqual(writes, set())
            self.assertEqual(snapshot(work), before)
        finally:
            temporary.cleanup()

    def test_no_legacy_or_network_imports(self):
        source = (ROOT / "packages" / "game-content" / "tools"
                  / "build_images.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            match = re.match(r"\s*(import|from)\s+(\S+)", line)
            if not match:
                continue
            module = match.group(2).split(".")[0]
            self.assertNotIn(module, ("get_game_config", "jsonpatch", "flask",
                                      "server", "command", "engine",
                                      "requests", "subprocess", "socket",
                                      "urllib", "webbrowser", "http"),
                             "forbidden import: " + line)


if __name__ == "__main__":
    unittest.main()
