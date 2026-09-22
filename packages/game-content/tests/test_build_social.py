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

import build_social as builder

EXPECTED_READS = frozenset([
    "config/main.json",
    "config/patch/patches.txt",
    "config/patch/atom_fusion_item.json",
    "config/patch/unit_patch.json",
    "config/patch/atom_fusion_items_data.json",
    "config/patch/atom_fusion_powerup.json",
    "config/patch/targets.json",
    "mods/mods.txt",
    "packages/game-content/schemas/neighbor_assist.schema.json",
    "packages/game-content/schemas/findable_item.schema.json",
    "packages/game-content/schemas/social_item.schema.json",
    "packages/game-content/manifest.json",
])

EXPECTED_WRITES = frozenset([
    "packages/game-content/normalized/neighbor_assists.json",
    "packages/game-content/normalized/findable_items.json",
    "packages/game-content/normalized/social_items.json",
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
    shutil.copy2(ROOT / "packages" / "game-content" / "tools" / "build_social.py",
                 work / "packages" / "game-content" / "tools" / "build_social.py")
    (work / "packages" / "game-content" / "schemas").mkdir(parents=True)
    for name in ("neighbor_assist.schema.json", "findable_item.schema.json",
                 "social_item.schema.json"):
        shutil.copy2(ROOT / "packages" / "game-content" / "schemas" / name,
                     work / "packages" / "game-content" / "schemas" / name)
    (work / "packages" / "game-content" / "normalized").mkdir(parents=True)
    shutil.copy2(ROOT / "packages" / "game-content" / "manifest.json",
                 work / "packages" / "game-content" / "manifest.json")
    return temporary, work


def read_work_json(work, relative):
    return json.loads((work / relative).read_text(encoding="utf-8"))


def write_work_json(work, relative, document):
    (work / relative).write_text(json.dumps(document), encoding="utf-8")


def load_work_table(work, key):
    return read_work_json(work, "config/main.json")[key]


def save_work_table(work, key, entries):
    document = read_work_json(work, "config/main.json")
    document[key] = entries
    write_work_json(work, "config/main.json", document)


class VerbatimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        layers = builder.load_all(str(ROOT))
        cls.layers = layers
        cls.assist = builder.coerce_assist(layers["neighbor_assists"][0], 0,
                                           "assist index 0")
        cls.findable = builder.coerce_findable(
            [entry for entry in layers["findable_items"] if entry["id"] == 1][0],
            "findable id 1")
        cls.social = builder.coerce_social(
            [entry for entry in layers["social_items"] if entry["id"] == 3][0],
            "social id 3")

    def test_assist_native_and_strings_verbatim(self):
        self.assertEqual(self.assist["position"], 0)
        self.assertEqual(self.assist["rnd"], 0)
        self.assertIs(type(self.assist["rnd"]), int)
        self.assertEqual(self.assist["reward"],
                         {"coins": 50, "cash": 0, "xp": 15})
        for field in ("coins", "cash", "xp"):
            self.assertIs(type(self.assist["reward"][field]), int)
        self.assertTrue(self.assist["task"].startswith("Help!"))
        self.assertTrue(self.assist["action"].startswith("Click OKAY"))

    def test_findable_native_and_strings_verbatim(self):
        self.assertEqual(self.findable["id"], 1)
        self.assertIs(type(self.findable["id"]), int)
        self.assertEqual(self.findable["coins"], 100)
        self.assertIs(type(self.findable["coins"]), int)
        self.assertEqual(self.findable["title"], "Clown")

    def test_social_native_and_strings_verbatim(self):
        self.assertEqual(self.social["id"], 3)
        self.assertIs(type(self.social["id"]), int)
        self.assertEqual(self.social["worker_cost"], 1)
        self.assertIs(type(self.social["worker_cost"]), int)
        self.assertEqual(self.social["workers"], "Oil QA Supervisor, Chemical")
        self.assertEqual(self.social["description"], "")

    def test_assist_rejects_bool_rnd(self):
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_assist(dict(self.layers["neighbor_assists"][0],
                                       rnd=True), 0, "mutated")

    def test_assist_rejects_string_reward_amount(self):
        mutated = dict(self.layers["neighbor_assists"][0])
        mutated["reward"] = dict(mutated["reward"], coins="50")
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_assist(mutated, 0, "mutated")

    def test_assist_rejects_negative_xp(self):
        mutated = dict(self.layers["neighbor_assists"][0])
        mutated["reward"] = dict(mutated["reward"], xp=-1)
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_assist(mutated, 0, "mutated")

    def test_assist_rejects_missing_reward_key(self):
        mutated = dict(self.layers["neighbor_assists"][0])
        reward = dict(mutated["reward"])
        del reward["cash"]
        mutated["reward"] = reward
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_assist(mutated, 0, "mutated")

    def test_findable_rejects_string_id(self):
        mutated = dict(self.layers["findable_items"][0])
        mutated["id"] = str(mutated["id"])
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_findable(mutated, "mutated")

    def test_findable_rejects_negative_coins(self):
        mutated = dict(self.layers["findable_items"][0])
        mutated["coins"] = -5
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_findable(mutated, "mutated")

    def test_social_rejects_string_cost(self):
        mutated = dict(self.layers["social_items"][0])
        mutated["worker_cost"] = "1"
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_social(mutated, "mutated")

    def test_social_rejects_empty_workers(self):
        mutated = dict(self.layers["social_items"][0])
        mutated["workers"] = ""
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_social(mutated, "mutated")


class ClassificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        layers = builder.load_all(str(ROOT))
        cls.layers = layers
        cls.social_section, cls.payloads = builder.build_package(
            str(ROOT), str(ROOT))

    def test_counts_match_verified_measurements(self):
        counts = self.social_section["counts"]
        self.assertEqual(counts["stored_assists"], 5)
        self.assertEqual(counts["stored_findables"], 10)
        self.assertEqual(counts["stored_socials"], 26)
        self.assertEqual(counts["assists"], 5)
        self.assertEqual(counts["findables"], 10)
        self.assertEqual(counts["socials"], 26)

    def test_assists_positional_with_uniform_reward(self):
        counts = self.social_section["counts"]
        self.assertEqual(counts["assist_reward_shapes"], 1)
        self.assertEqual(counts["assist_rnd_values"], [0])
        for entry in self.layers["neighbor_assists"]:
            self.assertNotIn("id", entry)
            self.assertEqual(entry["reward"], {"coins": 50, "cash": 0, "xp": 15})
            self.assertEqual(entry["rnd"], 0)

    def test_findables_sequential_ids_uniform_coins(self):
        counts = self.social_section["counts"]
        self.assertEqual(counts["findable_coins_values"], [100])
        self.assertEqual([entry["id"] for entry in self.layers["findable_items"]],
                         list(range(1, 11)))

    def test_socials_nonsequential_ids_uniform_empty_description(self):
        counts = self.social_section["counts"]
        self.assertEqual(counts["social_description_empty"], 26)
        self.assertEqual(counts["social_worker_costs"], [1, 2, 3])
        identifiers = [entry["id"] for entry in self.layers["social_items"]]
        self.assertEqual(len(set(identifiers)), 26)
        for entry in self.layers["social_items"]:
            self.assertEqual(entry["description"], "")
            self.assertTrue(entry["workers"])

    def test_no_patch_targets_social_content(self):
        self.assertEqual(self.social_section["inputs"]["social_patch_targets"],
                         "none")
        self.assertEqual(self.social_section["inputs"]["patch_order"],
                         ["atom_fusion_item", "unit_patch",
                          "atom_fusion_items_data", "atom_fusion_powerup",
                          "targets"])

    def test_envelope_fields_present(self):
        assists = json.loads(self.payloads[builder.ASSISTS_FILE])
        for position, item in enumerate(assists):
            for field in ("legacy_id", "kind", "source_file",
                          "source_layer", "content_version"):
                self.assertIn(field, item)
            self.assertEqual(item["kind"], "neighbor_assist")
            self.assertEqual(item["source_layer"], "stored")
            self.assertEqual(item["source_file"], "config/main.json")
            self.assertEqual(item["legacy_id"], str(position))
            self.assertEqual(item["position"], position)
            self.assertEqual(item["content_version"],
                             self.social_section["content_fingerprint"])
        findables = json.loads(self.payloads[builder.FINDABLES_FILE])
        for item in findables:
            self.assertEqual(item["kind"], "findable_item")
            self.assertEqual(item["legacy_id"], str(item["id"]))
        socials = json.loads(self.payloads[builder.SOCIAL_FILE])
        for item in socials:
            self.assertEqual(item["kind"], "social_item")
            self.assertEqual(item["legacy_id"], str(item["id"]))

    def test_legacy_id_forms(self):
        assists = json.loads(self.payloads[builder.ASSISTS_FILE])
        self.assertEqual([item["legacy_id"] for item in assists],
                         [str(position) for position in range(5)])
        findables = json.loads(self.payloads[builder.FINDABLES_FILE])
        self.assertEqual([item["legacy_id"] for item in findables],
                         [str(entry["id"]) for entry in
                          self.layers["findable_items"]])
        socials = json.loads(self.payloads[builder.SOCIAL_FILE])
        self.assertEqual([item["legacy_id"] for item in socials],
                         [str(entry["id"]) for entry in
                          self.layers["social_items"]])

    def test_entry_order_matches_stored(self):
        assists = json.loads(self.payloads[builder.ASSISTS_FILE])
        self.assertEqual([item["task"] for item in assists],
                         [entry["task"] for entry in
                          self.layers["neighbor_assists"]])
        socials = json.loads(self.payloads[builder.SOCIAL_FILE])
        self.assertEqual([item["workers"] for item in socials],
                         [entry["workers"] for entry in
                          self.layers["social_items"]])


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
        self.assertEqual(report["counts"]["assists"], 5)
        self.assertEqual(report["counts"]["findables"], 10)
        self.assertEqual(report["counts"]["socials"], 26)

    def test_negative_assist_amount_exit_1(self):
        entries = load_work_table(self.work, "neighbor_assists")
        entries[0]["reward"]["coins"] = -1
        save_work_table(self.work, "neighbor_assists", entries)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("coins", " ".join(json.loads(stdout)["problems"]))

    def test_missing_assist_field_exit_1(self):
        entries = load_work_table(self.work, "neighbor_assists")
        del entries[0]["task"]
        save_work_table(self.work, "neighbor_assists", entries)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("missing", " ".join(json.loads(stdout)["problems"]))

    def test_duplicate_findable_id_exit_1(self):
        entries = load_work_table(self.work, "findable_items")
        entries.append(dict(entries[0]))
        save_work_table(self.work, "findable_items", entries)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("duplicate", " ".join(json.loads(stdout)["problems"]))

    def test_negative_findable_coins_exit_1(self):
        entries = load_work_table(self.work, "findable_items")
        entries[0]["coins"] = -10
        save_work_table(self.work, "findable_items", entries)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("coins", " ".join(json.loads(stdout)["problems"]))

    def test_duplicate_social_id_exit_1(self):
        entries = load_work_table(self.work, "social_items")
        entries.append(dict(entries[0]))
        save_work_table(self.work, "social_items", entries)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("duplicate", " ".join(json.loads(stdout)["problems"]))

    def test_missing_social_field_exit_1(self):
        entries = load_work_table(self.work, "social_items")
        del entries[0]["workers"]
        save_work_table(self.work, "social_items", entries)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("missing", " ".join(json.loads(stdout)["problems"]))

    def test_failure_writes_nothing(self):
        before_manifest = (self.work / builder.MANIFEST_FILE).read_bytes()
        entries = load_work_table(self.work, "social_items")
        del entries[0]["workers"]
        save_work_table(self.work, "social_items", entries)
        code, _, _ = self.build()
        self.assertEqual(code, 1)
        for name in EXPECTED_WRITES:
            if name == "packages/game-content/manifest.json":
                continue
            self.assertFalse((self.work / name).exists(), name)
        self.assertEqual((self.work / builder.MANIFEST_FILE).read_bytes(),
                         before_manifest)

    def test_social_patch_target_exit_2(self):
        patch = self.work / "config" / "patch" / "targets.json"
        operations = json.loads(patch.read_text(encoding="utf-8"))
        operations.append({"op": "add", "path": "/social_items/-", "value": {}})
        patch.write_text(json.dumps(operations), encoding="utf-8")
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("social-table content", stderr)

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
        _social_section, payloads = builder.build_package(str(ROOT), str(ROOT))
        cls.assist_schema = json.loads(
            (ROOT / builder.ASSIST_SCHEMA_FILE).read_text(encoding="utf-8"))
        cls.findable_schema = json.loads(
            (ROOT / builder.FINDABLE_SCHEMA_FILE).read_text(encoding="utf-8"))
        cls.social_schema = json.loads(
            (ROOT / builder.SOCIAL_SCHEMA_FILE).read_text(encoding="utf-8"))
        cls.assist = json.loads(payloads[builder.ASSISTS_FILE])[0]
        cls.findable = json.loads(payloads[builder.FINDABLES_FILE])[0]
        cls.social = json.loads(payloads[builder.SOCIAL_FILE])[0]

    def schemas(self):
        return (("neighbor_assist", self.assist_schema, self.assist,
                 "neighbor_assist"),
                ("findable_item", self.findable_schema, self.findable,
                 "findable_item"),
                ("social_item", self.social_schema, self.social,
                 "social_item"))

    def test_required_is_subset_of_properties(self):
        for _kind, schema, _item, _label in self.schemas():
            for field in schema["required"]:
                self.assertIn(field, schema["properties"],
                              "required not in properties: " + field)

    def test_every_required_field_is_enforced(self):
        for kind, schema, item, label in self.schemas():
            for field in schema["required"]:
                mutated = dict(item)
                del mutated[field]
                problems = builder.validate_against_schema(
                    mutated, schema, label + " " + item["legacy_id"])
                self.assertTrue(
                    any("missing required field" in problem
                        and field in problem for problem in problems),
                    "no validator check for required field %s.%s"
                    % (kind, field))

    def test_wrong_types_are_rejected(self):
        assist_cases = [("position", "0"), ("task", 5), ("action", 7),
                        ("notification", []), ("rnd", "0"), ("reward", [])]
        for field, bad in assist_cases:
            mutated = dict(self.assist)
            mutated[field] = bad
            problems = builder.validate_against_schema(
                mutated, self.assist_schema,
                "neighbor_assist " + self.assist["legacy_id"])
            self.assertTrue(problems,
                            "no type check for neighbor_assist.%s" % (field,))
        findable_cases = [("id", "1"), ("title", 5), ("description", 7),
                          ("coins", "100")]
        for field, bad in findable_cases:
            mutated = dict(self.findable)
            mutated[field] = bad
            problems = builder.validate_against_schema(
                mutated, self.findable_schema,
                "findable_item " + self.findable["legacy_id"])
            self.assertTrue(problems,
                            "no type check for findable_item.%s" % (field,))
        social_cases = [("id", "3"), ("workers", 5), ("worker_cost", "1"),
                        ("description", 7)]
        for field, bad in social_cases:
            mutated = dict(self.social)
            mutated[field] = bad
            problems = builder.validate_against_schema(
                mutated, self.social_schema,
                "social_item " + self.social["legacy_id"])
            self.assertTrue(problems,
                            "no type check for social_item.%s" % (field,))

    def test_minimum_gates_enforced(self):
        mutated = dict(self.assist)
        mutated["rnd"] = -1
        self.assertTrue(builder.validate_against_schema(
            mutated, self.assist_schema, "neighbor_assist"))
        mutated = dict(self.findable)
        mutated["coins"] = -1
        self.assertTrue(builder.validate_against_schema(
            mutated, self.findable_schema, "findable_item"))
        mutated = dict(self.social)
        mutated["worker_cost"] = -1
        self.assertTrue(builder.validate_against_schema(
            mutated, self.social_schema, "social_item"))

    def test_kind_const_and_no_extra_properties(self):
        for schema, item, label in (
                (self.assist_schema, self.assist, "neighbor_assist"),
                (self.findable_schema, self.findable, "findable_item"),
                (self.social_schema, self.social, "social_item")):
            mutated = dict(item)
            mutated["kind"] = "building"
            self.assertTrue(builder.validate_against_schema(
                mutated, schema, label))
            mutated = dict(item)
            mutated["invented_field"] = 1
            problems = builder.validate_against_schema(
                mutated, schema, label)
            self.assertTrue(any("additional property" in problem
                                for problem in problems))


class RoundTripTests(unittest.TestCase):
    def test_round_trip_clean_on_real_content(self):
        layers = builder.load_all(str(ROOT))
        _social_section, payloads = builder.build_package(str(ROOT), str(ROOT))
        assists = json.loads(payloads[builder.ASSISTS_FILE])
        findables = json.loads(payloads[builder.FINDABLES_FILE])
        socials = json.loads(payloads[builder.SOCIAL_FILE])
        problems = builder.check_round_trip(assists, findables, socials,
                                            layers["neighbor_assists"],
                                            layers["findable_items"],
                                            layers["social_items"])
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
            self.assertIn("social", manifest)
            social_section = manifest["social"]
            self.assertEqual(social_section["result"], "success")
            self.assertEqual(social_section["policy"], builder.POLICY)
            self.assertEqual(social_section["coercion_ruleset"],
                             builder.COERCION_RULESET_VERSION)
            counts = social_section["counts"]
            assists = read_work_json(
                work, "packages/game-content/normalized/neighbor_assists.json")
            findables = read_work_json(
                work, "packages/game-content/normalized/findable_items.json")
            socials = read_work_json(
                work, "packages/game-content/normalized/social_items.json")
            self.assertEqual(len(assists), counts["assists"])
            self.assertEqual(len(findables), counts["findables"])
            self.assertEqual(len(socials), counts["socials"])
            self.assertEqual(counts["stored_assists"], counts["assists"])
            self.assertEqual(counts["stored_findables"], counts["findables"])
            self.assertEqual(counts["stored_socials"], counts["socials"])
            self.assertEqual(social_section["content_fingerprint"],
                             builder.fingerprint_inputs(
                                 builder.load_all(str(work))))
            by_file = {entry["file"]: entry
                       for entry in social_section["outputs"]}
            self.assertEqual(set(by_file),
                             set(EXPECTED_WRITES)
                             - {"packages/game-content/manifest.json"})
            for name in ("packages/game-content/normalized/neighbor_assists.json",
                         "packages/game-content/normalized/findable_items.json",
                         "packages/game-content/normalized/social_items.json"):
                data = (work / name).read_bytes()
                self.assertEqual(by_file[name]["bytes"], len(data), name)
                self.assertEqual(by_file[name]["sha256"],
                                 hashlib.sha256(data).hexdigest(), name)
            self.assertTrue(social_section["notes"])
            # Items, quests, tables, and economy keys survive the merge untouched.
            self.assertEqual(manifest["policy"], "items-normalization-v1")
            self.assertEqual(manifest["counts"]["loaded_items"], 900)
            self.assertEqual(manifest["quests"]["policy"],
                             "quest-normalization-v1")
            self.assertEqual(manifest["quests"]["counts"]["quests"], 91)
            self.assertEqual(manifest["tables"]["policy"],
                             "tables-normalization-v1")
            self.assertEqual(manifest["tables"]["counts"]["magics"], 10)
            self.assertEqual(manifest["economy"]["policy"],
                             "economy-normalization-v1")
            self.assertEqual(manifest["economy"]["counts"]["ranking_rewards"], 50)
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
                             {"packages/game-content/normalized/neighbor_assists.json",
                              "packages/game-content/normalized/findable_items.json",
                              "packages/game-content/normalized/social_items.json"})
            for path, payload in before.items():
                if path == "packages/game-content/manifest.json":
                    continue
                self.assertEqual(after[path], payload, path)
        finally:
            temporary.cleanup()

    def test_failure_writes_nothing_and_inputs_unchanged(self):
        temporary, work = make_work_tree()
        try:
            entries = load_work_table(work, "social_items")
            del entries[0]["workers"]
            save_work_table(work, "social_items", entries)
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
                  / "build_social.py").read_text(encoding="utf-8")
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
