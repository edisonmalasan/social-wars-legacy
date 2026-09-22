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

import build_taxonomy as builder

EXPECTED_READS = frozenset([
    "config/main.json",
    "config/patch/patches.txt",
    "config/patch/atom_fusion_item.json",
    "config/patch/unit_patch.json",
    "config/patch/atom_fusion_items_data.json",
    "config/patch/atom_fusion_powerup.json",
    "config/patch/targets.json",
    "mods/mods.txt",
    "packages/game-content/schemas/inventory_item.schema.json",
    "packages/game-content/schemas/category.schema.json",
    "packages/game-content/schemas/unit_collection_category.schema.json",
    "packages/game-content/normalized/buildings.json",
    "packages/game-content/normalized/units.json",
    "packages/game-content/normalized/specials.json",
    "packages/game-content/manifest.json",
])

EXPECTED_WRITES = frozenset([
    "packages/game-content/normalized/inventory_items.json",
    "packages/game-content/normalized/categories.json",
    "packages/game-content/normalized/unit_collection_categories.json",
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
    shutil.copy2(ROOT / "packages" / "game-content" / "tools" / "build_taxonomy.py",
                 work / "packages" / "game-content" / "tools" / "build_taxonomy.py")
    (work / "packages" / "game-content" / "schemas").mkdir(parents=True)
    for name in ("inventory_item.schema.json", "category.schema.json",
                 "unit_collection_category.schema.json"):
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


def load_work_object(work, key):
    return read_work_json(work, "config/main.json")[key]


def save_work_object(work, key, entries):
    document = read_work_json(work, "config/main.json")
    document[key] = entries
    write_work_json(work, "config/main.json", document)


class PredicateTests(unittest.TestCase):
    def test_numeric_grammar_matches_survey(self):
        self.assertEqual(builder.NUMERIC_GRAMMAR,
                         r"[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)"
                         r"(?:[eE][+-]?[0-9]+)?")

    def test_coerce_number_integral_becomes_int(self):
        self.assertEqual(builder.coerce_number_text("2", "probe"), 2)
        self.assertIs(type(builder.coerce_number_text("007", "probe")), int)

    def test_coerce_number_rejects_non_numeric(self):
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_number_text("Cement", "probe")


class CoercionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        layers = builder.load_all(str(ROOT))
        cls.layers = layers
        cls.inventory = builder.coerce_inventory(
            layers["inventory_items"]["1"], "1", "inventory key 1")
        cls.category = builder.coerce_category(
            layers["categories"]["1"], "1", "category key 1")
        cls.collection = builder.coerce_collection(
            layers["units_collections_categories"]["1"], "1",
            "collection key 1")

    def test_inventory_numerics_coerce_to_int(self):
        self.assertEqual(self.inventory["id"], 1)
        self.assertEqual(self.inventory["cashPrice"], 2)
        self.assertEqual(self.inventory["droppable"], 0)
        self.assertEqual(self.inventory["dropRate"], 2)
        self.assertEqual(self.inventory["dropsFrom"], 1)
        for field in ("id", "cashPrice", "droppable", "dropRate", "dropsFrom"):
            self.assertIs(type(self.inventory[field]), int)

    def test_inventory_strings_verbatim(self):
        self.assertEqual(self.inventory["name"], "Cement")
        self.assertTrue(self.inventory["description"])

    def test_inventory_rejects_non_integral_price(self):
        mutated = dict(self.layers["inventory_items"]["1"])
        mutated["cashPrice"] = "2.5"
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_inventory(mutated, "1", "mutated")

    def test_inventory_rejects_negative_rate(self):
        mutated = dict(self.layers["inventory_items"]["1"])
        mutated["dropRate"] = "-1"
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_inventory(mutated, "1", "mutated")

    def test_inventory_rejects_id_key_mismatch(self):
        mutated = dict(self.layers["inventory_items"]["1"])
        mutated["id"] = "2"
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_inventory(mutated, "1", "mutated")

    def test_category_native_fields_and_sub(self):
        self.assertEqual(self.category["id"], 1)
        self.assertIs(type(self.category["id"]), int)
        self.assertEqual(self.category["name"], "Village")
        self.assertEqual(len(self.category["sub"]), 5)
        for entry in self.category["sub"]:
            self.assertIs(type(entry["id"]), int)
            self.assertIsInstance(entry["name"], str)
            self.assertEqual(entry["parent"], 1)

    def test_category_rejects_parent_mismatch(self):
        mutated = json.loads(json.dumps(self.layers["categories"]["1"]))
        mutated["sub"][0]["parent"] = 2
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_category(mutated, "1", "mutated")

    def test_category_rejects_empty_sub(self):
        mutated = dict(self.layers["categories"]["1"])
        mutated["sub"] = []
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_category(mutated, "1", "mutated")

    def test_collection_native_fields_verbatim(self):
        self.assertEqual(self.collection["category_id"], 1)
        self.assertEqual(self.collection["rewards"], 0)
        self.assertEqual(self.collection["cost"], 1)
        self.assertIsNone(self.collection["costs"])
        self.assertEqual(self.collection["unit_refs"],
                         [str(value) for value in self.collection["units"]])

    def test_collection_rejects_string_category_id(self):
        mutated = dict(self.layers["units_collections_categories"]["2"])
        mutated["category_id"] = "2"
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_collection(mutated, "2", "mutated")

    def test_collection_rejects_non_integer_unit(self):
        mutated = dict(self.layers["units_collections_categories"]["2"])
        mutated["units"] = list(mutated["units"])
        mutated["units"][0] = "1007"
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_collection(mutated, "2", "mutated")


class ClassificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        layers = builder.load_all(str(ROOT))
        cls.layers = layers
        cls.taxonomy_section, cls.payloads = builder.build_package(
            str(ROOT), str(ROOT))

    def test_counts_match_verified_measurements(self):
        counts = self.taxonomy_section["counts"]
        self.assertEqual(counts["stored_inventory"], 90)
        self.assertEqual(counts["stored_categories"], 6)
        self.assertEqual(counts["stored_collections"], 20)
        self.assertEqual(counts["inventory"], 90)
        self.assertEqual(counts["categories"], 6)
        self.assertEqual(counts["collections"], 20)
        self.assertEqual(counts["category_sub_total"], 22)

    def test_inventory_string_encoded_source_shape(self):
        for key, entry in self.layers["inventory_items"].items():
            for field in ("id", "cashPrice", "droppable", "dropRate",
                          "dropsFrom", "name", "description"):
                self.assertIsInstance(entry[field], str, field)
            self.assertEqual(key, entry["id"])

    def test_categories_carry_sub_arrays(self):
        sizes = {key: len(entry["sub"])
                 for key, entry in self.layers["categories"].items()}
        self.assertEqual(sizes, {"1": 5, "2": 4, "3": 5, "4": 4, "5": 1,
                                 "12": 3})

    def test_collection_units_resolve_against_items(self):
        union = self.layers["items_id_set"]
        self.assertEqual(len(union), 900)
        self.assertEqual(self.taxonomy_section["counts"]["collection_units_total"],
                         89)
        for entry in self.layers["units_collections_categories"].values():
            for value in entry["units"]:
                self.assertIn(str(value), union)

    def test_collection_uniformity_notes(self):
        counts = self.taxonomy_section["counts"]
        self.assertEqual(counts["collection_el_empty"], 20)
        self.assertEqual(counts["collection_costs_null_keys"], ["1"])

    def test_category_gap_codes_recorded_not_failed(self):
        counts = self.taxonomy_section["counts"]
        self.assertEqual(counts["gap_category_codes"], ["6", "7", "8", "9"])
        self.assertEqual(counts["gap_subcategory_codes"],
                         ["6", "7", "81", "91"])

    def test_inventory_ids_edge_counts(self):
        edge = self.taxonomy_section["inputs"]["inventory_reference_edge"]
        self.assertEqual(edge["stored_items"], 778)
        self.assertEqual(edge["inventory_ids_objects"], 3)
        self.assertEqual(edge["inventory_ids_null"], 775)

    def test_no_patch_targets_taxonomy_content(self):
        self.assertEqual(self.taxonomy_section["inputs"]["taxonomy_patch_targets"],
                         "none")
        self.assertEqual(self.taxonomy_section["inputs"]["patch_order"],
                         ["atom_fusion_item", "unit_patch",
                          "atom_fusion_items_data", "atom_fusion_powerup",
                          "targets"])

    def test_envelope_fields_present(self):
        inventory = json.loads(self.payloads[builder.INVENTORY_FILE])
        for item in inventory:
            for field in ("legacy_id", "kind", "source_file",
                          "source_layer", "content_version"):
                self.assertIn(field, item)
            self.assertEqual(item["kind"], "inventory_item")
            self.assertEqual(item["source_layer"], "stored")
            self.assertEqual(item["source_file"], "config/main.json")
            self.assertEqual(item["legacy_id"], str(item["id"]))
            self.assertEqual(item["content_version"],
                             self.taxonomy_section["content_fingerprint"])
        categories = json.loads(self.payloads[builder.CATEGORIES_FILE])
        for item in categories:
            self.assertEqual(item["kind"], "category")
            self.assertEqual(item["legacy_id"], str(item["id"]))
        collections = json.loads(self.payloads[builder.COLLECTIONS_FILE])
        for item in collections:
            self.assertEqual(item["kind"], "unit_collection_category")
            self.assertEqual(item["legacy_id"], str(item["category_id"]))
            self.assertEqual(item["unit_refs"],
                             [str(value) for value in item["units"]])

    def test_legacy_key_order_matches_stored_document(self):
        inventory = json.loads(self.payloads[builder.INVENTORY_FILE])
        self.assertEqual([item["legacy_id"] for item in inventory],
                         list(self.layers["inventory_items"].keys()))
        categories = json.loads(self.payloads[builder.CATEGORIES_FILE])
        self.assertEqual([item["legacy_id"] for item in categories],
                         list(self.layers["categories"].keys()))
        collections = json.loads(self.payloads[builder.COLLECTIONS_FILE])
        self.assertEqual([item["legacy_id"] for item in collections],
                         list(self.layers["units_collections_categories"].keys()))


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
        self.assertEqual(report["counts"]["inventory"], 90)
        self.assertEqual(report["counts"]["categories"], 6)
        self.assertEqual(report["counts"]["collections"], 20)

    def test_negative_inventory_amount_exit_1(self):
        entries = load_work_object(self.work, "inventory_items")
        entries["1"]["cashPrice"] = "-2"
        save_work_object(self.work, "inventory_items", entries)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("cashPrice", " ".join(json.loads(stdout)["problems"]))

    def test_missing_inventory_field_exit_1(self):
        entries = load_work_object(self.work, "inventory_items")
        del entries["1"]["name"]
        save_work_object(self.work, "inventory_items", entries)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("missing", " ".join(json.loads(stdout)["problems"]))

    def test_category_parent_mismatch_exit_1(self):
        entries = load_work_object(self.work, "categories")
        entries["1"]["sub"][0]["parent"] = 2
        save_work_object(self.work, "categories", entries)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("parent", " ".join(json.loads(stdout)["problems"]))

    def test_unresolvable_collection_reference_exit_1(self):
        entries = load_work_object(self.work, "units_collections_categories")
        entries["2"]["units"] = [999999]
        save_work_object(self.work, "units_collections_categories", entries)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("unresolvable", " ".join(json.loads(stdout)["problems"]))

    def test_unresolvable_inventory_ids_key_exit_1(self):
        document = read_work_json(self.work, "config/main.json")
        document["items"][0]["inventory_ids"] = '{"no_such_inv_xyz": 1}'
        write_work_json(self.work, "config/main.json", document)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("unresolvable", " ".join(json.loads(stdout)["problems"]))

    def test_missing_collection_field_exit_1(self):
        entries = load_work_object(self.work, "units_collections_categories")
        del entries["2"]["units"]
        save_work_object(self.work, "units_collections_categories", entries)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("missing", " ".join(json.loads(stdout)["problems"]))

    def test_failure_writes_nothing(self):
        before_manifest = (self.work / builder.MANIFEST_FILE).read_bytes()
        entries = load_work_object(self.work, "inventory_items")
        del entries["1"]["name"]
        save_work_object(self.work, "inventory_items", entries)
        code, _, _ = self.build()
        self.assertEqual(code, 1)
        for name in EXPECTED_WRITES:
            if name == "packages/game-content/manifest.json":
                continue
            self.assertFalse((self.work / name).exists(), name)
        self.assertEqual((self.work / builder.MANIFEST_FILE).read_bytes(),
                         before_manifest)

    def test_taxonomy_patch_target_exit_2(self):
        patch = self.work / "config" / "patch" / "targets.json"
        operations = json.loads(patch.read_text(encoding="utf-8"))
        operations.append({"op": "add", "path": "/categories/new",
                           "value": {}})
        patch.write_text(json.dumps(operations), encoding="utf-8")
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("taxonomy content", stderr)

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

    def test_missing_items_edge_exit_2(self):
        (self.work / "packages" / "game-content" / "normalized"
         / "units.json").unlink()
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("normalized items", stderr)


class TraceabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _taxonomy_section, payloads = builder.build_package(str(ROOT), str(ROOT))
        cls.inventory_schema = json.loads(
            (ROOT / builder.INVENTORY_SCHEMA_FILE).read_text(encoding="utf-8"))
        cls.category_schema = json.loads(
            (ROOT / builder.CATEGORY_SCHEMA_FILE).read_text(encoding="utf-8"))
        cls.collection_schema = json.loads(
            (ROOT / builder.COLLECTION_SCHEMA_FILE).read_text(encoding="utf-8"))
        cls.inventory = json.loads(payloads[builder.INVENTORY_FILE])[0]
        cls.category = json.loads(payloads[builder.CATEGORIES_FILE])[0]
        cls.collection = json.loads(payloads[builder.COLLECTIONS_FILE])[0]

    def schemas(self):
        return (("inventory_item", self.inventory_schema, self.inventory,
                 "inventory_item"),
                ("category", self.category_schema, self.category, "category"),
                ("unit_collection_category", self.collection_schema,
                 self.collection, "unit_collection_category"))

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
        inventory_cases = [("id", "1"), ("name", 5), ("cashPrice", "2"),
                           ("droppable", "0"), ("dropRate", "2"),
                           ("dropsFrom", "1"), ("description", 7)]
        for field, bad in inventory_cases:
            mutated = dict(self.inventory)
            mutated[field] = bad
            problems = builder.validate_against_schema(
                mutated, self.inventory_schema,
                "inventory_item " + self.inventory["legacy_id"])
            self.assertTrue(problems,
                            "no type check for inventory_item.%s" % (field,))
        category_cases = [("id", "1"), ("name", 5), ("sub", {})]
        for field, bad in category_cases:
            mutated = dict(self.category)
            mutated[field] = bad
            problems = builder.validate_against_schema(
                mutated, self.category_schema,
                "category " + self.category["legacy_id"])
            self.assertTrue(problems,
                            "no type check for category.%s" % (field,))
        collection_cases = [("category_id", "1"), ("units", "1007"),
                            ("unit_refs", "1007"), ("rewards", "0"),
                            ("cost", "1"), ("costs", 5), ("position", "10"),
                            ("category_name", 5), ("category_name_el", 7)]
        for field, bad in collection_cases:
            mutated = dict(self.collection)
            mutated[field] = bad
            problems = builder.validate_against_schema(
                mutated, self.collection_schema,
                "unit_collection_category " + self.collection["legacy_id"])
            self.assertTrue(problems,
                            "no type check for unit_collection_category.%s"
                            % (field,))

    def test_minimum_and_size_gates_enforced(self):
        mutated = dict(self.inventory)
        mutated["cashPrice"] = -1
        self.assertTrue(builder.validate_against_schema(
            mutated, self.inventory_schema, "inventory_item"))
        mutated = dict(self.category)
        mutated["sub"] = []
        problems = builder.validate_against_schema(
            mutated, self.category_schema, "category")
        self.assertTrue(any("minItems" in problem for problem in problems))
        mutated = dict(self.collection)
        mutated["units"] = []
        problems = builder.validate_against_schema(
            mutated, self.collection_schema, "unit_collection_category")
        self.assertTrue(any("minItems" in problem for problem in problems))
        mutated = dict(self.collection)
        mutated["cost"] = -1
        self.assertTrue(builder.validate_against_schema(
            mutated, self.collection_schema, "unit_collection_category"))

    def test_kind_const_and_no_extra_properties(self):
        for schema, item, label in (
                (self.inventory_schema, self.inventory, "inventory_item"),
                (self.category_schema, self.category, "category"),
                (self.collection_schema, self.collection,
                 "unit_collection_category")):
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
        _taxonomy_section, payloads = builder.build_package(str(ROOT), str(ROOT))
        inventory = json.loads(payloads[builder.INVENTORY_FILE])
        categories = json.loads(payloads[builder.CATEGORIES_FILE])
        collections = json.loads(payloads[builder.COLLECTIONS_FILE])
        problems = builder.check_round_trip(
            inventory, categories, collections,
            {"inventory item": list(layers["inventory_items"].keys()),
             "category": list(layers["categories"].keys()),
             "collection": list(layers["units_collections_categories"].keys())},
            layers["inventory_items"], layers["categories"],
            layers["units_collections_categories"])
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
            self.assertIn("taxonomy", manifest)
            taxonomy_section = manifest["taxonomy"]
            self.assertEqual(taxonomy_section["result"], "success")
            self.assertEqual(taxonomy_section["policy"], builder.POLICY)
            self.assertEqual(taxonomy_section["coercion_ruleset"],
                             builder.COERCION_RULESET_VERSION)
            counts = taxonomy_section["counts"]
            inventory = read_work_json(
                work, "packages/game-content/normalized/inventory_items.json")
            categories = read_work_json(
                work, "packages/game-content/normalized/categories.json")
            collections = read_work_json(
                work, "packages/game-content/normalized/unit_collection_categories.json")
            self.assertEqual(len(inventory), counts["inventory"])
            self.assertEqual(len(categories), counts["categories"])
            self.assertEqual(len(collections), counts["collections"])
            self.assertEqual(counts["stored_inventory"], counts["inventory"])
            self.assertEqual(counts["stored_categories"], counts["categories"])
            self.assertEqual(counts["stored_collections"], counts["collections"])
            self.assertEqual(taxonomy_section["content_fingerprint"],
                             builder.fingerprint_inputs(
                                 builder.load_all(str(work))))
            self.assertEqual(taxonomy_section["inputs"]["items_reference_edge"]["union_legacy_ids"],
                             900)
            by_file = {entry["file"]: entry
                       for entry in taxonomy_section["outputs"]}
            self.assertEqual(set(by_file),
                             set(EXPECTED_WRITES)
                             - {"packages/game-content/manifest.json"})
            for name in ("packages/game-content/normalized/inventory_items.json",
                         "packages/game-content/normalized/categories.json",
                         "packages/game-content/normalized/unit_collection_categories.json"):
                data = (work / name).read_bytes()
                self.assertEqual(by_file[name]["bytes"], len(data), name)
                self.assertEqual(by_file[name]["sha256"],
                                 hashlib.sha256(data).hexdigest(), name)
            self.assertTrue(taxonomy_section["notes"])
            # Prior keys survive the taxonomy merge untouched.
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
            self.assertEqual(manifest["social"]["policy"],
                             "social-normalization-v1")
            self.assertEqual(manifest["social"]["counts"]["socials"], 26)
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
                             {"packages/game-content/normalized/inventory_items.json",
                              "packages/game-content/normalized/categories.json",
                              "packages/game-content/normalized/unit_collection_categories.json"})
            for path, payload in before.items():
                if path == "packages/game-content/manifest.json":
                    continue
                self.assertEqual(after[path], payload, path)
        finally:
            temporary.cleanup()

    def test_failure_writes_nothing_and_inputs_unchanged(self):
        temporary, work = make_work_tree()
        try:
            entries = load_work_object(work, "inventory_items")
            del entries["1"]["name"]
            save_work_object(work, "inventory_items", entries)
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
                  / "build_taxonomy.py").read_text(encoding="utf-8")
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
