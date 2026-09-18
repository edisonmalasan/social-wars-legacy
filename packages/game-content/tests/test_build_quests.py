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

import build_quests as builder

EXPECTED_READS = frozenset([
    "config/main.json",
    "config/patch/patches.txt",
    "config/patch/atom_fusion_item.json",
    "config/patch/unit_patch.json",
    "config/patch/atom_fusion_items_data.json",
    "config/patch/atom_fusion_powerup.json",
    "config/patch/targets.json",
    "mods/mods.txt",
    "packages/game-content/schemas/quest.schema.json",
    "packages/game-content/schemas/collection.schema.json",
    "packages/game-content/normalized/buildings.json",
    "packages/game-content/normalized/units.json",
    "packages/game-content/normalized/specials.json",
    "packages/game-content/manifest.json",
])

EXPECTED_WRITES = frozenset([
    "packages/game-content/normalized/quests.json",
    "packages/game-content/normalized/collections.json",
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
    shutil.copy2(ROOT / "packages" / "game-content" / "tools" / "build_quests.py",
                 work / "packages" / "game-content" / "tools" / "build_quests.py")
    (work / "packages" / "game-content" / "schemas").mkdir(parents=True)
    for name in ("quest.schema.json", "collection.schema.json"):
        shutil.copy2(ROOT / "packages" / "game-content" / "schemas" / name,
                     work / "packages" / "game-content" / "schemas" / name)
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


def load_work_goals(work):
    return read_work_json(work, "config/main.json")["goals"]


def save_work_goals(work, goals):
    document = read_work_json(work, "config/main.json")
    document["goals"] = goals
    write_work_json(work, "config/main.json", document)


def load_work_collections(work):
    return read_work_json(work, "config/main.json")["collections"]


def save_work_collections(work, collections):
    document = read_work_json(work, "config/main.json")
    document["collections"] = collections
    write_work_json(work, "config/main.json", document)


class PredicateTests(unittest.TestCase):
    def test_numeric_grammar_matches_survey(self):
        self.assertEqual(builder.NUMERIC_GRAMMAR,
                         r"[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)"
                         r"(?:[eE][+-]?[0-9]+)?")

    def test_numeric_accepts_plain_signed_and_exponent(self):
        for text in ("0", "35", "007", "10", "3.14", ".7", "1e3"):
            self.assertTrue(builder.is_string_encoded_number(text),
                            "should be numeric: %r" % (text,))

    def test_numeric_rejects_words_blanks_and_dates(self):
        for text in ("", "Draggy Collection", "-", "collection description 1",
                      " 12", "12 "):
            self.assertFalse(builder.is_string_encoded_number(text),
                             "should not be numeric: %r" % (text,))

    def test_embedded_json_accepts_arrays_objects_and_numbers(self):
        for text in ("[66,67,68,69,70]", '{"1085":1}', "35", "1"):
            self.assertTrue(builder.is_embedded_json_string(text),
                            "should be embedded json: %r" % (text,))
        self.assertFalse(builder.is_embedded_json_string(""))

    def test_embedded_json_rejects_plain_words(self):
        for text in ("Draggy Collection", "-", "{broken"):
            self.assertFalse(builder.is_embedded_json_string(text),
                             "should not be embedded json: %r" % (text,))

    def test_coerce_number_integral_becomes_int(self):
        self.assertEqual(builder.coerce_number_text("35", "probe"), 35)
        self.assertIs(type(builder.coerce_number_text("35", "probe")), int)
        self.assertEqual(builder.coerce_number_text("007", "probe"), 7)

    def test_coerce_number_rejects_non_numeric(self):
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_number_text("Draggy Collection", "probe")


class CoercionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        layers = builder.load_all(str(ROOT))
        cls.goals = layers["goals"]
        cls.collections = layers["collections"]
        by_goal = {entry["id"]: entry for entry in layers["goals"]}
        cls.first_quest = builder.coerce_quest(by_goal[1], "goal id 1")
        by_collection = {entry["id"]: entry for entry in layers["collections"]}
        cls.first_collection = builder.coerce_collection(
            by_collection["1"], "collection id '1'")

    def test_quest_native_fields_kept_verbatim(self):
        self.assertEqual(self.first_quest["id"], 1)
        self.assertIs(type(self.first_quest["id"]), int)
        self.assertEqual(self.first_quest["reward"], 10)
        self.assertIs(type(self.first_quest["reward"]), int)
        self.assertEqual(self.first_quest["title"], "Build a farm")
        self.assertIsInstance(self.first_quest["hint"], str)
        self.assertIsInstance(self.first_quest["description"], str)

    def test_quest_uniform_hint_and_reward_preserved(self):
        hints = {entry["hint"] for entry in self.goals}
        rewards = {entry["reward"] for entry in self.goals}
        self.assertEqual(hints, {""})
        self.assertEqual(rewards, {10})
        body = builder.coerce_quest(self.goals[0], "sample")
        self.assertEqual(body["hint"], "")
        self.assertEqual(body["reward"], 10)

    def test_quest_rejects_string_encoded_id(self):
        mutated = dict(self.goals[0])
        mutated["id"] = str(mutated["id"])
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_quest(mutated, "mutated")

    def test_collection_id_and_price_coerce_to_int(self):
        self.assertEqual(self.first_collection["id"], 1)
        self.assertIs(type(self.first_collection["id"]), int)
        self.assertEqual(self.first_collection["cashPrice"], 35)
        self.assertIs(type(self.first_collection["cashPrice"]), int)

    def test_collection_item_ids_coerce_to_int_array(self):
        self.assertEqual(self.first_collection["item_ids"], [66, 67, 68, 69, 70])
        for value in self.first_collection["item_ids"]:
            self.assertIs(type(value), int)

    def test_collection_prize_coerces_to_object(self):
        self.assertEqual(self.first_collection["prize"], {"1085": 1})

    def test_collection_names_verbatim(self):
        self.assertEqual(self.first_collection["name"], "Draggy Collection")
        self.assertEqual(self.first_collection["description"],
                         "collection description 1")

    def test_collection_rejects_non_integral_price(self):
        mutated = dict(self.collections[0])
        mutated["cashPrice"] = "3.5"
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_collection(mutated, "mutated")

    def test_collection_rejects_empty_item_ids(self):
        mutated = dict(self.collections[0])
        mutated["item_ids"] = "[]"
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_collection(mutated, "mutated")

    def test_collection_rejects_zero_prize_amount(self):
        mutated = dict(self.collections[0])
        mutated["prize"] = '{"1085":0}'
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_collection(mutated, "mutated")


class ClassificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        layers = builder.load_all(str(ROOT))
        cls.layers = layers
        cls.quest_section, cls.payloads = builder.build_package(
            str(ROOT), str(ROOT))

    def test_counts_match_verified_measurements(self):
        counts = self.quest_section["counts"]
        self.assertEqual(counts["stored_goals"], 91)
        self.assertEqual(counts["stored_collections"], 10)
        self.assertEqual(counts["quests"], 91)
        self.assertEqual(counts["collections"], 10)

    def test_goals_native_ids_and_uniform_fields(self):
        counts = self.quest_section["counts"]
        self.assertEqual(counts["hint_empty"], 91)
        self.assertEqual(counts["reward_values"], [10])
        for entry in self.layers["goals"]:
            self.assertIs(type(entry["id"]), int)
            self.assertIs(type(entry["reward"]), int)
        identifiers = [entry["id"] for entry in self.layers["goals"]]
        self.assertEqual(len(set(identifiers)), 91)

    def test_collections_string_encoded_source_shape(self):
        for entry in self.layers["collections"]:
            self.assertIsInstance(entry["id"], str)
            self.assertIsInstance(entry["cashPrice"], str)
            self.assertIsInstance(entry["item_ids"], str)
            self.assertIsInstance(entry["prize"], str)
        identifiers = [entry["id"] for entry in self.layers["collections"]]
        self.assertEqual(len(set(identifiers)), 10)

    def test_all_collection_references_resolve(self):
        known = self.layers["known_ids"]
        unresolved = []
        for entry in self.layers["collections"]:
            for value in json.loads(entry["item_ids"]):
                if str(value) not in known:
                    unresolved.append(value)
            for key in json.loads(entry["prize"]):
                if str(key) not in known:
                    unresolved.append(key)
        self.assertEqual(unresolved, [])

    def test_reference_edge_union_matches_items_package(self):
        edge = self.quest_section["inputs"]["items_reference_edge"]
        self.assertEqual(edge["counts"]["buildings"], 470)
        self.assertEqual(edge["counts"]["units"], 429)
        self.assertEqual(edge["counts"]["specials"], 1)
        self.assertEqual(edge["union_legacy_ids"], 900)

    def test_no_patch_targets_quest_content(self):
        self.assertEqual(self.quest_section["inputs"]["quest_patch_targets"],
                         "none")
        self.assertEqual(self.quest_section["inputs"]["patch_order"],
                         ["atom_fusion_item", "unit_patch",
                          "atom_fusion_items_data", "atom_fusion_powerup",
                          "targets"])

    def test_envelope_fields_present(self):
        quests = json.loads(self.payloads[builder.QUESTS_FILE])
        for item in quests[:5] + quests[-5:]:
            for field in ("legacy_id", "kind", "source_file",
                          "source_layer", "content_version"):
                self.assertIn(field, item)
            self.assertEqual(item["kind"], "quest")
            self.assertEqual(item["source_layer"], "stored")
            self.assertEqual(item["source_file"], "config/main.json")
            self.assertEqual(item["content_version"],
                             self.quest_section["content_fingerprint"])
            self.assertEqual(item["legacy_id"], str(item["id"]))
        collections = json.loads(self.payloads[builder.COLLECTIONS_FILE])
        for item in collections:
            self.assertEqual(item["kind"], "collection")
            self.assertEqual(item["legacy_id"], str(item["id"]))
            self.assertEqual(item["item_refs"],
                             [str(value) for value in item["item_ids"]])
            self.assertEqual(item["prize_refs"],
                             sorted(item["prize"].keys()))

    def test_legacy_id_forms(self):
        quests = json.loads(self.payloads[builder.QUESTS_FILE])
        self.assertEqual({item["legacy_id"] for item in quests},
                         {str(entry["id"]) for entry in self.layers["goals"]})
        collections = json.loads(self.payloads[builder.COLLECTIONS_FILE])
        self.assertEqual([item["legacy_id"] for item in collections],
                         [entry["id"] for entry in self.layers["collections"]])


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
        self.assertEqual(report["counts"]["quests"], 91)
        self.assertEqual(report["counts"]["collections"], 10)

    def test_duplicate_quest_id_exit_1_and_writes_nothing(self):
        goals = load_work_goals(self.work)
        goals.append(dict(goals[0]))
        save_work_goals(self.work, goals)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("duplicate", json.loads(stdout)["problems"][0])
        self.assertFalse((self.work / builder.QUESTS_FILE).exists())
        self.assertFalse((self.work / builder.COLLECTIONS_FILE).exists())

    def test_duplicate_collection_id_exit_1(self):
        collections = load_work_collections(self.work)
        collections.append(dict(collections[0]))
        save_work_collections(self.work, collections)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("duplicate", json.loads(stdout)["problems"][0])

    def test_unresolvable_item_reference_exit_1(self):
        collections = load_work_collections(self.work)
        collections[0]["item_ids"] = "[99991,99992,99993,99994,99995]"
        save_work_collections(self.work, collections)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("unresolvable",
                      " ".join(json.loads(stdout)["problems"]))

    def test_unresolvable_prize_reference_exit_1(self):
        collections = load_work_collections(self.work)
        collections[0]["prize"] = '{"99991":1}'
        save_work_collections(self.work, collections)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("unresolvable",
                      " ".join(json.loads(stdout)["problems"]))

    def test_negative_cash_price_exit_1(self):
        collections = load_work_collections(self.work)
        collections[0]["cashPrice"] = "-5"
        save_work_collections(self.work, collections)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("cashPrice", " ".join(json.loads(stdout)["problems"]))

    def test_bad_prize_amount_exit_1(self):
        collections = load_work_collections(self.work)
        collections[0]["prize"] = '{"1085":0}'
        save_work_collections(self.work, collections)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("prize amount",
                      " ".join(json.loads(stdout)["problems"]))

    def test_missing_quest_field_exit_1(self):
        goals = load_work_goals(self.work)
        del goals[0]["title"]
        save_work_goals(self.work, goals)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("missing", " ".join(json.loads(stdout)["problems"]))

    def test_missing_collection_field_exit_1(self):
        collections = load_work_collections(self.work)
        del collections[0]["prize"]
        save_work_collections(self.work, collections)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("missing", " ".join(json.loads(stdout)["problems"]))

    def test_failure_writes_nothing(self):
        before_manifest = (self.work / builder.MANIFEST_FILE).read_bytes()
        goals = load_work_goals(self.work)
        del goals[0]["title"]
        save_work_goals(self.work, goals)
        code, _, _ = self.build()
        self.assertEqual(code, 1)
        self.assertFalse((self.work / builder.QUESTS_FILE).exists())
        self.assertFalse((self.work / builder.COLLECTIONS_FILE).exists())
        self.assertEqual((self.work / builder.MANIFEST_FILE).read_bytes(),
                         before_manifest)

    def test_quest_patch_target_exit_2(self):
        patch = self.work / "config" / "patch" / "targets.json"
        operations = json.loads(patch.read_text(encoding="utf-8"))
        operations.append({"op": "add", "path": "/goals/-", "value": {}})
        patch.write_text(json.dumps(operations), encoding="utf-8")
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("quest content", stderr)

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
        quest_section, payloads = builder.build_package(str(ROOT), str(ROOT))
        cls.quest_schema = json.loads(
            (ROOT / builder.QUEST_SCHEMA_FILE).read_text(encoding="utf-8"))
        cls.collection_schema = json.loads(
            (ROOT / builder.COLLECTION_SCHEMA_FILE).read_text(encoding="utf-8"))
        cls.quest = json.loads(payloads[builder.QUESTS_FILE])[0]
        cls.collection = json.loads(payloads[builder.COLLECTIONS_FILE])[0]

    def schemas(self):
        return (("quest", self.quest_schema, self.quest, "quest"),
                ("collection", self.collection_schema, self.collection,
                 "collection"))

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
        quest_cases = [("id", "2"), ("title", 5), ("hint", 7),
                       ("description", []), ("reward", "10")]
        for field, bad in quest_cases:
            mutated = dict(self.quest)
            mutated[field] = bad
            problems = builder.validate_against_schema(
                mutated, self.quest_schema, "quest " + self.quest["legacy_id"])
            self.assertTrue(problems,
                            "no type check for quest.%s" % (field,))
        collection_cases = [("id", "1"), ("name", 5), ("item_ids", "[1]"),
                            ("item_refs", "x"), ("prize", [1]),
                            ("prize_refs", {}), ("cashPrice", "35")]
        for field, bad in collection_cases:
            mutated = dict(self.collection)
            mutated[field] = bad
            problems = builder.validate_against_schema(
                mutated, self.collection_schema,
                "collection " + self.collection["legacy_id"])
            self.assertTrue(problems,
                            "no type check for collection.%s" % (field,))

    def test_minimum_and_size_gates_enforced(self):
        mutated = dict(self.quest)
        mutated["reward"] = -1
        self.assertTrue(builder.validate_against_schema(
            mutated, self.quest_schema, "quest"))
        mutated = dict(self.collection)
        mutated["cashPrice"] = -1
        self.assertTrue(builder.validate_against_schema(
            mutated, self.collection_schema, "collection"))
        mutated = dict(self.collection)
        mutated["item_ids"] = []
        self.assertTrue(builder.validate_against_schema(
            mutated, self.collection_schema, "collection"))
        mutated = dict(self.collection)
        mutated["prize"] = {}
        self.assertTrue(builder.validate_against_schema(
            mutated, self.collection_schema, "collection"))
        mutated = dict(self.collection)
        mutated["prize"] = {"1085": 0}
        self.assertTrue(builder.validate_against_schema(
            mutated, self.collection_schema, "collection"))

    def test_kind_const_and_no_extra_properties(self):
        for schema, item, label in (
                (self.quest_schema, self.quest, "quest"),
                (self.collection_schema, self.collection, "collection")):
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
        quest_section, payloads = builder.build_package(str(ROOT), str(ROOT))
        quests = json.loads(payloads[builder.QUESTS_FILE])
        collections = json.loads(payloads[builder.COLLECTIONS_FILE])
        problems = builder.check_round_trip(quests, collections,
                                            layers["goals"],
                                            layers["collections"])
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
            self.assertIn("quests", manifest)
            quest_section = manifest["quests"]
            self.assertEqual(quest_section["result"], "success")
            self.assertEqual(quest_section["policy"], builder.POLICY)
            self.assertEqual(quest_section["coercion_ruleset"],
                             builder.COERCION_RULESET_VERSION)
            counts = quest_section["counts"]
            quests = read_work_json(
                work, "packages/game-content/normalized/quests.json")
            collections = read_work_json(
                work, "packages/game-content/normalized/collections.json")
            self.assertEqual(len(quests), counts["quests"])
            self.assertEqual(len(collections), counts["collections"])
            self.assertEqual(counts["stored_goals"], counts["quests"])
            self.assertEqual(counts["stored_collections"], counts["collections"])
            self.assertEqual(quest_section["content_fingerprint"],
                             builder.fingerprint_inputs(
                                 builder.load_all(str(work))))
            by_file = {entry["file"]: entry
                       for entry in quest_section["outputs"]}
            self.assertEqual(set(by_file),
                             set(EXPECTED_WRITES)
                             - {"packages/game-content/manifest.json"})
            for name in ("packages/game-content/normalized/quests.json",
                         "packages/game-content/normalized/collections.json"):
                data = (work / name).read_bytes()
                self.assertEqual(by_file[name]["bytes"], len(data), name)
                self.assertEqual(by_file[name]["sha256"],
                                 hashlib.sha256(data).hexdigest(), name)
            edge = quest_section["inputs"]["items_reference_edge"]
            self.assertEqual(sorted(edge["files"]),
                             sorted(["packages/game-content/normalized/buildings.json",
                                     "packages/game-content/normalized/units.json",
                                     "packages/game-content/normalized/specials.json"]))
            self.assertEqual(edge["union_legacy_ids"], 900)
            self.assertTrue(quest_section["notes"])
            # Items keys survive the quest merge untouched.
            self.assertEqual(manifest["policy"], "items-normalization-v1")
            self.assertEqual(manifest["counts"]["loaded_items"], 900)
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
                             {"packages/game-content/normalized/quests.json",
                              "packages/game-content/normalized/collections.json"})
            for path, payload in before.items():
                if path == "packages/game-content/manifest.json":
                    continue
                self.assertEqual(after[path], payload, path)
        finally:
            temporary.cleanup()

    def test_failure_writes_nothing_and_inputs_unchanged(self):
        temporary, work = make_work_tree()
        try:
            collections = load_work_collections(work)
            collections[0]["item_ids"] = "[99991,99992,99993,99994,99995]"
            save_work_collections(work, collections)
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
                  / "build_quests.py").read_text(encoding="utf-8")
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
