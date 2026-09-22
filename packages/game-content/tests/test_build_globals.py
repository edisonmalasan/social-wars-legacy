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

import build_globals as builder

EXPECTED_READS = frozenset([
    "config/main.json",
    "config/patch/patches.txt",
    "config/patch/atom_fusion_item.json",
    "config/patch/unit_patch.json",
    "config/patch/atom_fusion_items_data.json",
    "config/patch/atom_fusion_powerup.json",
    "config/patch/targets.json",
    "mods/mods.txt",
    "packages/game-content/schemas/global_entry.schema.json",
    "packages/game-content/manifest.json",
])

EXPECTED_WRITES = frozenset([
    "packages/game-content/normalized/globals.json",
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
    shutil.copy2(ROOT / "packages" / "game-content" / "tools" / "build_globals.py",
                 work / "packages" / "game-content" / "tools" / "build_globals.py")
    (work / "packages" / "game-content" / "schemas").mkdir(parents=True)
    shutil.copy2(ROOT / "packages" / "game-content" / "schemas" / "global_entry.schema.json",
                 work / "packages" / "game-content" / "schemas" / "global_entry.schema.json")
    (work / "packages" / "game-content" / "normalized").mkdir(parents=True)
    shutil.copy2(ROOT / "packages" / "game-content" / "manifest.json",
                 work / "packages" / "game-content" / "manifest.json")
    return temporary, work


def read_work_json(work, relative):
    return json.loads((work / relative).read_text(encoding="utf-8"))


def write_work_json(work, relative, document):
    (work / relative).write_text(json.dumps(document), encoding="utf-8")


def load_work_powerup(work):
    return read_work_json(work, "config/patch/atom_fusion_powerup.json")


def save_work_powerup(work, operations):
    write_work_json(work, "config/patch/atom_fusion_powerup.json", operations)


class LayeringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        layers = builder.load_all(str(ROOT))
        cls.layers = layers

    def test_stored_hundred_four_loaded_hundred_five(self):
        self.assertEqual(len(self.layers["stored_globals"]), 104)
        self.assertEqual(len(self.layers["loaded_globals"]), 105)
        self.assertIn(builder.POWERUP_KEY, self.layers["loaded_globals"])
        self.assertNotIn(builder.POWERUP_KEY, self.layers["stored_globals"])

    def test_patch_order_and_single_add(self):
        self.assertEqual(self.layers["patch_names"],
                         ["atom_fusion_item", "unit_patch",
                          "atom_fusion_items_data", "atom_fusion_powerup",
                          "targets"])
        operations = json.loads(
            (ROOT / "config" / "patch" / "atom_fusion_powerup.json").read_text(
                encoding="utf-8"))
        self.assertEqual(len(operations), 1)
        self.assertEqual(operations[0]["op"], "add")
        self.assertEqual(operations[0]["path"], builder.POWERUP_PATH)
        self.assertEqual(len(operations[0]["value"]), 6)


class VerbatimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        layers = builder.load_all(str(ROOT))
        cls.layers = layers
        cls.integer = builder.coerce_global("CONSTRUCTING_TIME", 1000,
                                            "stored", "probe")
        cls.schedule = builder.coerce_global(
            builder.POWERUP_KEY,
            layers["loaded_globals"][builder.POWERUP_KEY],
            builder.PATCHED_LAYER, "probe")
        cls.opaque = builder.coerce_global(
            "NEWFRIENDS_REWARD_ID_UNIT",
            layers["loaded_globals"]["NEWFRIENDS_REWARD_ID_UNIT"],
            "stored", "probe")

    def test_integer_typed_verbatim(self):
        self.assertEqual(self.integer["value"], 1000)
        self.assertIs(type(self.integer["value"]), int)
        self.assertEqual(self.integer["value_type"], "integer")
        self.assertEqual(self.integer["layer"], "stored")

    def test_float_records_number(self):
        body = builder.coerce_global(
            "MARKET_INCREMENT",
            self.layers["loaded_globals"]["MARKET_INCREMENT"],
            "stored", "probe")
        self.assertEqual(body["value_type"], "number")
        self.assertIsInstance(body["value"], float)

    def test_patch_schedule_layer_and_rows(self):
        self.assertEqual(self.schedule["layer"], builder.PATCHED_LAYER)
        self.assertEqual(self.schedule["value_type"], "array")
        self.assertEqual(len(self.schedule["value"]), 6)
        self.assertEqual(self.schedule["value"][0],
                         {"cash_cost": 1, "order_increment": 1})

    def test_strings_opaque_verbatim(self):
        self.assertEqual(self.opaque["value_type"], "string")
        self.assertEqual(self.opaque["value"],
                         self.layers["loaded_globals"]["NEWFRIENDS_REWARD_ID_UNIT"])
        self.assertEqual(self.opaque["value"], "1046.1, 1055.1, 1048.1, 1050.2, 1051.1")

    def test_bool_never_integer(self):
        self.assertEqual(builder.value_type_of(True), "boolean")
        self.assertEqual(builder.value_type_of(1), "integer")

    def test_rejects_empty_key(self):
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_global("", 1, "stored", "mutated")


class ClassificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        layers = builder.load_all(str(ROOT))
        cls.layers = layers
        cls.globals_section, cls.payloads = builder.build_package(
            str(ROOT), str(ROOT))

    def test_counts_and_type_distribution(self):
        counts = self.globals_section["counts"]
        self.assertEqual(counts["stored_globals"], 104)
        self.assertEqual(counts["loaded_globals"], 105)
        self.assertEqual(counts["globals"], 105)
        self.assertEqual(counts["value_types"],
                         {"integer": 62, "number": 4, "string": 8,
                          "array": 23, "object": 8})

    def test_string_keys_recorded(self):
        self.assertEqual(self.globals_section["counts"]["string_keys"],
                         ["DEPOT_LIMITS", "LIMITED_EDITION_EXPIRATION",
                          "NEWFRIENDS_REWARD_DESCRIPTION",
                          "NEWFRIENDS_REWARD_ID_UNIT",
                          "NEWFRIENDS_REWARD_SCALE_UNIT", "NEWS_IMAGE",
                          "NEWS_STORE", "URL_APP_PROD"])

    def test_envelope_fields_present(self):
        entries = json.loads(self.payloads[builder.GLOBALS_FILE])
        for item in entries:
            for field in ("legacy_id", "kind", "source_file",
                          "source_layer", "content_version"):
                self.assertIn(field, item)
            self.assertEqual(item["kind"], "global_entry")
            self.assertEqual(item["legacy_id"], item["key"])
            self.assertEqual(item["content_version"],
                             self.globals_section["content_fingerprint"])
        patched = [item for item in entries
                   if item["legacy_id"] == builder.POWERUP_KEY]
        self.assertEqual(len(patched), 1)
        self.assertEqual(patched[0]["source_layer"], builder.PATCHED_LAYER)
        self.assertEqual(patched[0]["source_file"],
                         "config/patch/atom_fusion_powerup.json")
        stored = [item for item in entries
                  if item["legacy_id"] != builder.POWERUP_KEY]
        self.assertEqual(len(stored), 104)
        for item in stored:
            self.assertEqual(item["source_layer"], "stored")
            self.assertEqual(item["source_file"], "config/main.json")

    def test_key_order_matches_loaded_object(self):
        entries = json.loads(self.payloads[builder.GLOBALS_FILE])
        self.assertEqual([item["legacy_id"] for item in entries],
                         list(self.layers["loaded_globals"].keys()))
        self.assertEqual(entries[-1]["legacy_id"], builder.POWERUP_KEY)


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
        self.assertEqual(report["counts"]["globals"], 105)

    def test_corrupt_schema_exit_2(self):
        schema = read_work_json(self.work,
                                "packages/game-content/schemas/global_entry.schema.json")
        del schema["properties"]["value"]
        write_work_json(self.work,
                        "packages/game-content/schemas/global_entry.schema.json",
                        schema)
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("required not in properties", stderr)

    def test_divergent_powerup_shape_exit_2(self):
        operations = load_work_powerup(self.work)
        operations[0]["value"] = [{"cash_cost": 1}]
        save_work_powerup(self.work, operations)
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("row keys drift", stderr)

    def test_extra_globals_target_exit_2(self):
        operations = load_work_powerup(self.work)
        operations.append({"op": "add", "path": "/globals/EXTRA", "value": 1})
        save_work_powerup(self.work, operations)
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("exactly one add", stderr)

    def test_non_powerup_globals_patch_exit_2(self):
        patch = self.work / "config" / "patch" / "targets.json"
        operations = json.loads(patch.read_text(encoding="utf-8"))
        operations.append({"op": "add", "path": "/globals/EXTRA", "value": 1})
        patch.write_text(json.dumps(operations), encoding="utf-8")
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("globals content", stderr)

    def test_active_mod_exit_2(self):
        mods = self.work / "mods" / "mods.txt"
        mods.write_text(mods.read_text(encoding="utf-8") + "\nno_hiring_needed\n",
                        encoding="utf-8")
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("active mods", stderr)

    def test_unparseable_powerup_exit_2(self):
        (self.work / "config" / "patch" / "atom_fusion_powerup.json").write_text(
            "{broken", encoding="utf-8")
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("not valid json", stderr)

    def test_failure_writes_nothing(self):
        before_manifest = (self.work / builder.MANIFEST_FILE).read_bytes()
        operations = load_work_powerup(self.work)
        operations[0]["value"] = [{"cash_cost": 1}]
        save_work_powerup(self.work, operations)
        code, _, _ = self.build()
        self.assertEqual(code, 2)
        for name in EXPECTED_WRITES:
            if name == "packages/game-content/manifest.json":
                continue
            self.assertFalse((self.work / name).exists(), name)
        self.assertEqual((self.work / builder.MANIFEST_FILE).read_bytes(),
                         before_manifest)


class TraceabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _globals_section, payloads = builder.build_package(str(ROOT), str(ROOT))
        cls.globals_schema = json.loads(
            (ROOT / builder.GLOBALS_SCHEMA_FILE).read_text(encoding="utf-8"))
        cls.entry = json.loads(payloads[builder.GLOBALS_FILE])[0]

    def test_required_is_subset_of_properties(self):
        for field in self.globals_schema["required"]:
            self.assertIn(field, self.globals_schema["properties"],
                          "required not in properties: " + field)

    def test_every_required_field_is_enforced(self):
        for field in self.globals_schema["required"]:
            mutated = dict(self.entry)
            del mutated[field]
            problems = builder.validate_against_schema(
                mutated, self.globals_schema,
                "global_entry " + self.entry["legacy_id"])
            self.assertTrue(
                any("missing required field" in problem
                    and field in problem for problem in problems),
                "no validator check for required field global_entry.%s" % (field,))

    def test_wrong_types_are_rejected(self):
        cases = [("key", 5), ("value_type", 5), ("value", b"bytes"),
                 ("source_layer", 5)]
        for field, bad in cases:
            mutated = dict(self.entry)
            mutated[field] = bad
            problems = builder.validate_against_schema(
                mutated, self.globals_schema,
                "global_entry " + self.entry["legacy_id"])
            self.assertTrue(problems,
                            "no type check for global_entry.%s" % (field,))

    def test_union_accepts_every_observed_type(self):
        samples = {"integer": 1, "number": 1.5, "string": "x", "array": [1],
                   "object": {"a": 1}, "boolean": True, "null": None}
        for value_type, value in samples.items():
            mutated = dict(self.entry)
            mutated["value_type"] = value_type
            mutated["value"] = value
            problems = builder.validate_against_schema(
                mutated, self.globals_schema,
                "global_entry " + self.entry["legacy_id"])
            self.assertEqual(problems, [],
                             "union rejects %s: %r" % (value_type, problems))

    def test_value_type_value_mismatch_rejected(self):
        mutated = dict(self.entry)
        mutated["value_type"] = "integer"
        mutated["value"] = "1000"
        problems = builder.validate_against_schema(
            mutated, self.globals_schema,
            "global_entry " + self.entry["legacy_id"])
        self.assertTrue(any("value_type/value mismatch" in problem
                            for problem in problems))

    def test_layer_enum_and_kind_const_enforced(self):
        mutated = dict(self.entry)
        mutated["source_layer"] = "patched(targets)"
        problems = builder.validate_against_schema(
            mutated, self.globals_schema, "global_entry")
        self.assertTrue(any("enum mismatch" in problem for problem in problems))
        mutated = dict(self.entry)
        mutated["kind"] = "building"
        self.assertTrue(builder.validate_against_schema(
            mutated, self.globals_schema, "global_entry"))
        mutated = dict(self.entry)
        mutated["invented_field"] = 1
        problems = builder.validate_against_schema(
            mutated, self.globals_schema, "global_entry")
        self.assertTrue(any("additional property" in problem
                            for problem in problems))


class RoundTripTests(unittest.TestCase):
    def test_round_trip_clean_on_real_content(self):
        layers = builder.load_all(str(ROOT))
        _globals_section, payloads = builder.build_package(str(ROOT), str(ROOT))
        entries = json.loads(payloads[builder.GLOBALS_FILE])
        problems = builder.check_round_trip(entries,
                                            list(layers["loaded_globals"].keys()),
                                            layers["loaded_globals"])
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
            self.assertIn("globals", manifest)
            globals_section = manifest["globals"]
            self.assertEqual(globals_section["result"], "success")
            self.assertEqual(globals_section["policy"], builder.POLICY)
            self.assertEqual(globals_section["coercion_ruleset"],
                             builder.COERCION_RULESET_VERSION)
            counts = globals_section["counts"]
            entries = read_work_json(
                work, "packages/game-content/normalized/globals.json")
            self.assertEqual(len(entries), counts["globals"])
            self.assertEqual(counts["stored_globals"], 104)
            self.assertEqual(counts["loaded_globals"], 105)
            self.assertEqual(globals_section["content_fingerprint"],
                             builder.fingerprint_inputs(
                                 builder.load_all(str(work))))
            self.assertEqual(globals_section["inputs"]["globals_layering"], "add")
            by_file = {entry["file"]: entry
                       for entry in globals_section["outputs"]}
            self.assertEqual(set(by_file),
                             set(EXPECTED_WRITES)
                             - {"packages/game-content/manifest.json"})
            data = (work / "packages/game-content/normalized/globals.json").read_bytes()
            self.assertEqual(by_file["packages/game-content/normalized/globals.json"]["bytes"],
                             len(data))
            self.assertEqual(by_file["packages/game-content/normalized/globals.json"]["sha256"],
                             hashlib.sha256(data).hexdigest())
            self.assertTrue(globals_section["notes"])
            # Prior keys survive the globals merge untouched.
            self.assertEqual(manifest["policy"], "items-normalization-v1")
            self.assertEqual(manifest["counts"]["loaded_items"], 900)
            self.assertEqual(manifest["quests"]["policy"],
                             "quest-normalization-v1")
            self.assertEqual(manifest["tables"]["policy"],
                             "tables-normalization-v1")
            self.assertEqual(manifest["economy"]["policy"],
                             "economy-normalization-v1")
            self.assertEqual(manifest["social"]["policy"],
                             "social-normalization-v1")
            self.assertEqual(manifest["taxonomy"]["policy"],
                             "taxonomy-normalization-v1")
            self.assertEqual(manifest["darts"]["policy"],
                             "darts-normalization-v1")
            self.assertEqual(manifest["darts"]["counts"]["darts"], 27)
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
                             {"packages/game-content/normalized/globals.json"})
            for path, payload in before.items():
                if path == "packages/game-content/manifest.json":
                    continue
                self.assertEqual(after[path], payload, path)
        finally:
            temporary.cleanup()

    def test_failure_writes_nothing_and_inputs_unchanged(self):
        temporary, work = make_work_tree()
        try:
            operations = load_work_powerup(work)
            operations[0]["value"] = [{"cash_cost": 1}]
            save_work_powerup(work, operations)
            code, _, _, opened, before = self.guarded_run(
                work, ["--repo-root", str(work), "--out-root", str(work)])
            self.assertEqual(code, 2)
            _reads, writes = self.observed_sets(work, opened)
            self.assertEqual(writes, set())
            self.assertEqual(snapshot(work), before)
        finally:
            temporary.cleanup()

    def test_no_legacy_or_network_imports(self):
        source = (ROOT / "packages" / "game-content" / "tools"
                  / "build_globals.py").read_text(encoding="utf-8")
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
