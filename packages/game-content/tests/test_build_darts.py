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

import build_darts as builder

EXPECTED_READS = frozenset([
    "config/main.json",
    "config/patch/patches.txt",
    "config/patch/atom_fusion_item.json",
    "config/patch/unit_patch.json",
    "config/patch/atom_fusion_items_data.json",
    "config/patch/atom_fusion_powerup.json",
    "config/patch/targets.json",
    "mods/mods.txt",
    "packages/game-content/schemas/darts_item.schema.json",
    "packages/game-content/normalized/buildings.json",
    "packages/game-content/normalized/units.json",
    "packages/game-content/normalized/specials.json",
    "packages/game-content/manifest.json",
])

EXPECTED_WRITES = frozenset([
    "packages/game-content/normalized/darts_items.json",
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
    shutil.copy2(ROOT / "packages" / "game-content" / "tools" / "build_darts.py",
                 work / "packages" / "game-content" / "tools" / "build_darts.py")
    (work / "packages" / "game-content" / "schemas").mkdir(parents=True)
    shutil.copy2(ROOT / "packages" / "game-content" / "schemas" / "darts_item.schema.json",
                 work / "packages" / "game-content" / "schemas" / "darts_item.schema.json")
    (work / "packages" / "game-content" / "normalized").mkdir(parents=True)
    for name in ("buildings.json", "units.json", "specials.json"):
        shutil.copy2(ROOT / "packages" / "game-content" / "normalized" / name,
                     work / "packages" / "game-content" / "normalized" / name)
    shutil.copy2(ROOT / "packages" / "game-content" / "manifest.json",
                 work / "packages" / "game-content" / "manifest.json")
    return temporary, work


def read_work_json(work, relative):
    return json.loads((work / relative).read_text(encoding="utf-8"))


def write_work_json(work, relative, document):
    (work / relative).write_text(json.dumps(document), encoding="utf-8")


def load_work_targets(work):
    return read_work_json(work, "config/patch/targets.json")


def save_work_targets(work, operations):
    write_work_json(work, "config/patch/targets.json", operations)


class LayeringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        layers = builder.load_all(str(ROOT))
        cls.layers = layers

    def test_stored_thirty_patched_twenty_seven(self):
        self.assertEqual(len(self.layers["stored_darts"]), 30)
        self.assertEqual(len(self.layers["patched_darts"]), 27)

    def test_patch_order_and_single_replace(self):
        self.assertEqual(self.layers["patch_names"],
                         ["atom_fusion_item", "unit_patch",
                          "atom_fusion_items_data", "atom_fusion_powerup",
                          "targets"])
        operations = json.loads(
            (ROOT / "config" / "patch" / "targets.json").read_text(encoding="utf-8"))
        self.assertEqual(len(operations), 1)
        self.assertEqual(operations[0]["op"], "replace")
        self.assertEqual(operations[0]["path"], "/darts_items")

    def test_patched_ids_sequential(self):
        self.assertEqual([entry["id"] for entry in self.layers["patched_darts"]],
                         list(range(1, 28)))


class VerbatimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        layers = builder.load_all(str(ROOT))
        cls.layers = layers
        cls.first = builder.coerce_darts(
            [entry for entry in layers["patched_darts"] if entry["id"] == 1][0],
            "darts id 1")

    def test_pools_and_extra_verbatim(self):
        self.assertEqual(self.first["id"], 1)
        self.assertIs(type(self.first["id"]), int)
        self.assertEqual(self.first["items"], [1061, 1073, 1071, 1031, 1058, 1045])
        for value in self.first["items"]:
            self.assertIs(type(value), int)
        self.assertEqual(self.first["extra_item"], 1152)
        self.assertIs(type(self.first["extra_item"]), int)
        self.assertEqual(self.first["item_refs"],
                         ["1061", "1073", "1071", "1031", "1058", "1045"])
        self.assertEqual(self.first["extra_ref"], "1152")

    def test_start_date_verbatim_input(self):
        self.assertEqual(self.first["start_date"], "2012-03-02 23:00:00")

    def test_rejects_string_id(self):
        mutated = dict(self.layers["patched_darts"][0])
        mutated["id"] = "1"
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_darts(mutated, "mutated")

    def test_rejects_bool_pool_element(self):
        mutated = dict(self.layers["patched_darts"][0])
        mutated["items"] = list(mutated["items"])
        mutated["items"][0] = True
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_darts(mutated, "mutated")

    def test_rejects_empty_pool(self):
        mutated = dict(self.layers["patched_darts"][0])
        mutated["items"] = []
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_darts(mutated, "mutated")

    def test_rejects_string_extra(self):
        mutated = dict(self.layers["patched_darts"][0])
        mutated["extra_item"] = "1152"
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_darts(mutated, "mutated")

    def test_rejects_empty_start_date(self):
        mutated = dict(self.layers["patched_darts"][0])
        mutated["start_date"] = ""
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_darts(mutated, "mutated")


class ClassificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        layers = builder.load_all(str(ROOT))
        cls.layers = layers
        cls.darts_section, cls.payloads = builder.build_package(
            str(ROOT), str(ROOT))

    def test_counts_match_verified_measurements(self):
        counts = self.darts_section["counts"]
        self.assertEqual(counts["stored_darts"], 30)
        self.assertEqual(counts["patched_darts"], 27)
        self.assertEqual(counts["darts"], 27)
        self.assertEqual(counts["pool_sizes"], [6])

    def test_pools_resolve_against_items(self):
        union = self.layers["items_id_set"]
        self.assertEqual(len(union), 900)
        darts = json.loads(self.payloads[builder.DARTS_FILE])
        for item in darts:
            for key in item["item_refs"]:
                self.assertIn(key, union)
            self.assertIn(item["extra_ref"], union)
            self.assertEqual(item["item_refs"],
                             [str(value) for value in item["items"]])
            self.assertEqual(item["extra_ref"], str(item["extra_item"]))

    def test_envelope_fields_present(self):
        darts = json.loads(self.payloads[builder.DARTS_FILE])
        for item in darts:
            for field in ("legacy_id", "kind", "source_file",
                          "source_layer", "content_version"):
                self.assertIn(field, item)
            self.assertEqual(item["kind"], "darts_item")
            self.assertEqual(item["source_layer"], "patched(targets)")
            self.assertEqual(item["source_file"], "config/patch/targets.json")
            self.assertEqual(item["legacy_id"], str(item["id"]))
            self.assertEqual(item["content_version"],
                             self.darts_section["content_fingerprint"])

    def test_order_matches_patched_array(self):
        darts = json.loads(self.payloads[builder.DARTS_FILE])
        self.assertEqual([item["legacy_id"] for item in darts],
                         [str(entry["id"]) for entry in
                          self.layers["patched_darts"]])
        self.assertEqual([item["start_date"] for item in darts],
                         [entry["start_date"] for entry in
                          self.layers["patched_darts"]])


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
        self.assertEqual(report["counts"]["darts"], 27)

    def test_duplicate_patched_id_exit_1(self):
        operations = load_work_targets(self.work)
        value = operations[0]["value"]
        value.append(dict(value[0]))
        save_work_targets(self.work, operations)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("duplicate", " ".join(json.loads(stdout)["problems"]))

    def test_unresolvable_pool_reference_exit_1(self):
        operations = load_work_targets(self.work)
        operations[0]["value"][0]["items"] = [999999, 1073, 1071, 1031, 1058, 1045]
        save_work_targets(self.work, operations)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("unresolvable", " ".join(json.loads(stdout)["problems"]))

    def test_unresolvable_extra_reference_exit_1(self):
        operations = load_work_targets(self.work)
        operations[0]["value"][0]["extra_item"] = 999999
        save_work_targets(self.work, operations)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("unresolvable", " ".join(json.loads(stdout)["problems"]))

    def test_missing_darts_field_exit_1(self):
        operations = load_work_targets(self.work)
        del operations[0]["value"][0]["extra_item"]
        save_work_targets(self.work, operations)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("missing", " ".join(json.loads(stdout)["problems"]))

    def test_failure_writes_nothing(self):
        before_manifest = (self.work / builder.MANIFEST_FILE).read_bytes()
        operations = load_work_targets(self.work)
        del operations[0]["value"][0]["extra_item"]
        save_work_targets(self.work, operations)
        code, _, _ = self.build()
        self.assertEqual(code, 1)
        for name in EXPECTED_WRITES:
            if name == "packages/game-content/manifest.json":
                continue
            self.assertFalse((self.work / name).exists(), name)
        self.assertEqual((self.work / builder.MANIFEST_FILE).read_bytes(),
                         before_manifest)

    def test_extra_darts_target_exit_2(self):
        operations = load_work_targets(self.work)
        operations.append({"op": "add", "path": "/darts_items/-", "value": {}})
        save_work_targets(self.work, operations)
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("exactly one replace", stderr)

    def test_non_targets_darts_patch_exit_2(self):
        patch = self.work / "config" / "patch" / "atom_fusion_powerup.json"
        operations = json.loads(patch.read_text(encoding="utf-8"))
        operations.append({"op": "add", "path": "/darts_items/-", "value": {}})
        patch.write_text(json.dumps(operations), encoding="utf-8")
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("darts content", stderr)

    def test_active_mod_exit_2(self):
        mods = self.work / "mods" / "mods.txt"
        mods.write_text(mods.read_text(encoding="utf-8") + "\nno_hiring_needed\n",
                        encoding="utf-8")
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("active mods", stderr)

    def test_unparseable_targets_exit_2(self):
        (self.work / "config" / "patch" / "targets.json").write_text("{broken",
                                                                     encoding="utf-8")
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("not valid json", stderr)

    def test_missing_items_edge_exit_2(self):
        (self.work / "packages" / "game-content" / "normalized"
         / "specials.json").unlink()
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("normalized items", stderr)


class TraceabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _darts_section, payloads = builder.build_package(str(ROOT), str(ROOT))
        cls.darts_schema = json.loads(
            (ROOT / builder.DARTS_SCHEMA_FILE).read_text(encoding="utf-8"))
        cls.darts = json.loads(payloads[builder.DARTS_FILE])[0]

    def test_required_is_subset_of_properties(self):
        for field in self.darts_schema["required"]:
            self.assertIn(field, self.darts_schema["properties"],
                          "required not in properties: " + field)

    def test_every_required_field_is_enforced(self):
        for field in self.darts_schema["required"]:
            mutated = dict(self.darts)
            del mutated[field]
            problems = builder.validate_against_schema(
                mutated, self.darts_schema,
                "darts_item " + self.darts["legacy_id"])
            self.assertTrue(
                any("missing required field" in problem
                    and field in problem for problem in problems),
                "no validator check for required field darts_item.%s" % (field,))

    def test_wrong_types_are_rejected(self):
        cases = [("id", "1"), ("start_date", 5), ("items", "1061"),
                 ("item_refs", "1061"), ("extra_item", "1152"),
                 ("extra_ref", 1152)]
        for field, bad in cases:
            mutated = dict(self.darts)
            mutated[field] = bad
            problems = builder.validate_against_schema(
                mutated, self.darts_schema,
                "darts_item " + self.darts["legacy_id"])
            self.assertTrue(problems,
                            "no type check for darts_item.%s" % (field,))

    def test_minimum_and_size_gates_enforced(self):
        mutated = dict(self.darts)
        mutated["id"] = -1
        self.assertTrue(builder.validate_against_schema(
            mutated, self.darts_schema, "darts_item"))
        mutated = dict(self.darts)
        mutated["items"] = []
        problems = builder.validate_against_schema(
            mutated, self.darts_schema, "darts_item")
        self.assertTrue(any("minItems" in problem for problem in problems))
        mutated = dict(self.darts)
        mutated["item_refs"] = [1061]
        problems = builder.validate_against_schema(
            mutated, self.darts_schema, "darts_item")
        self.assertTrue(problems)

    def test_kind_const_and_no_extra_properties(self):
        mutated = dict(self.darts)
        mutated["kind"] = "building"
        self.assertTrue(builder.validate_against_schema(
            mutated, self.darts_schema, "darts_item"))
        mutated = dict(self.darts)
        mutated["invented_field"] = 1
        problems = builder.validate_against_schema(
            mutated, self.darts_schema, "darts_item")
        self.assertTrue(any("additional property" in problem
                            for problem in problems))


class RoundTripTests(unittest.TestCase):
    def test_round_trip_clean_on_real_content(self):
        layers = builder.load_all(str(ROOT))
        _darts_section, payloads = builder.build_package(str(ROOT), str(ROOT))
        darts = json.loads(payloads[builder.DARTS_FILE])
        problems = builder.check_round_trip(darts, layers["patched_darts"])
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
            self.assertIn("darts", manifest)
            darts_section = manifest["darts"]
            self.assertEqual(darts_section["result"], "success")
            self.assertEqual(darts_section["policy"], builder.POLICY)
            self.assertEqual(darts_section["coercion_ruleset"],
                             builder.COERCION_RULESET_VERSION)
            counts = darts_section["counts"]
            darts = read_work_json(
                work, "packages/game-content/normalized/darts_items.json")
            self.assertEqual(len(darts), counts["darts"])
            self.assertEqual(counts["stored_darts"], 30)
            self.assertEqual(counts["patched_darts"], 27)
            self.assertEqual(darts_section["content_fingerprint"],
                             builder.fingerprint_inputs(
                                 builder.load_all(str(work))))
            self.assertEqual(darts_section["inputs"]["items_reference_edge"]["union_legacy_ids"],
                             900)
            self.assertEqual(darts_section["inputs"]["darts_layering"], "replace")
            by_file = {entry["file"]: entry
                       for entry in darts_section["outputs"]}
            self.assertEqual(set(by_file),
                             set(EXPECTED_WRITES)
                             - {"packages/game-content/manifest.json"})
            data = (work / "packages/game-content/normalized/darts_items.json").read_bytes()
            self.assertEqual(by_file["packages/game-content/normalized/darts_items.json"]["bytes"],
                             len(data))
            self.assertEqual(by_file["packages/game-content/normalized/darts_items.json"]["sha256"],
                             hashlib.sha256(data).hexdigest())
            self.assertTrue(darts_section["notes"])
            # Prior keys survive the darts merge untouched.
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
            self.assertEqual(manifest["taxonomy"]["counts"]["collections"], 20)
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
                             {"packages/game-content/normalized/darts_items.json"})
            for path, payload in before.items():
                if path == "packages/game-content/manifest.json":
                    continue
                self.assertEqual(after[path], payload, path)
        finally:
            temporary.cleanup()

    def test_failure_writes_nothing_and_inputs_unchanged(self):
        temporary, work = make_work_tree()
        try:
            operations = json.loads(
                (work / "config" / "patch" / "targets.json").read_text(encoding="utf-8"))
            del operations[0]["value"][0]["extra_item"]
            (work / "config" / "patch" / "targets.json").write_text(
                json.dumps(operations), encoding="utf-8")
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
                  / "build_darts.py").read_text(encoding="utf-8")
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
