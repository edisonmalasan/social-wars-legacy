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

import build_economy as builder

EXPECTED_READS = frozenset([
    "config/main.json",
    "config/patch/patches.txt",
    "config/patch/atom_fusion_item.json",
    "config/patch/unit_patch.json",
    "config/patch/atom_fusion_items_data.json",
    "config/patch/atom_fusion_powerup.json",
    "config/patch/targets.json",
    "mods/mods.txt",
    "packages/game-content/schemas/expansion_price.schema.json",
    "packages/game-content/schemas/town_price.schema.json",
    "packages/game-content/schemas/map_price.schema.json",
    "packages/game-content/schemas/level_ranking_reward.schema.json",
    "packages/game-content/normalized/buildings.json",
    "packages/game-content/normalized/units.json",
    "packages/game-content/normalized/specials.json",
    "packages/game-content/manifest.json",
])

EXPECTED_WRITES = frozenset([
    "packages/game-content/normalized/expansion_prices.json",
    "packages/game-content/normalized/town_prices.json",
    "packages/game-content/normalized/map_prices.json",
    "packages/game-content/normalized/level_ranking_reward.json",
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
    shutil.copy2(ROOT / "packages" / "game-content" / "tools" / "build_economy.py",
                 work / "packages" / "game-content" / "tools" / "build_economy.py")
    (work / "packages" / "game-content" / "schemas").mkdir(parents=True)
    for name in ("expansion_price.schema.json", "town_price.schema.json",
                 "map_price.schema.json", "level_ranking_reward.schema.json"):
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


def load_work_schedule(work, key):
    return read_work_json(work, "config/main.json")[key]


def save_work_schedule(work, key, entries):
    document = read_work_json(work, "config/main.json")
    document[key] = entries
    write_work_json(work, "config/main.json", document)


class VerbatimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        layers = builder.load_all(str(ROOT))
        cls.layers = layers
        cls.expansion = builder.coerce_expansion(layers["expansion_prices"][0], 0,
                                                 "expansion price index 0")
        cls.town = builder.coerce_town(layers["town_prices"][0], 0,
                                       "town price index 0")
        cls.map = builder.coerce_map(layers["map_prices"][0], 0,
                                     "map price index 0")
        cls.ranking = builder.coerce_ranking(layers["level_ranking_reward"][0],
                                             "ranking reward level 50")

    def test_expansion_native_amounts_verbatim(self):
        self.assertEqual(self.expansion["position"], 0)
        self.assertEqual(
            (self.expansion["coins"], self.expansion["cash"],
             self.expansion["neighbors"], self.expansion["inventory_qte"]),
            (0, 0, 0, 0))
        for field in ("coins", "cash", "neighbors", "inventory_qte"):
            self.assertIs(type(self.expansion[field]), int)

    def test_town_native_amounts_verbatim(self):
        self.assertEqual(
            (self.town["coins"], self.town["cash"], self.town["level"]),
            (100000, 20, 15))
        for field in ("coins", "cash", "level"):
            self.assertIs(type(self.town[field]), int)

    def test_map_native_amounts_verbatim(self):
        self.assertEqual(
            (self.map["coins"], self.map["cash"], self.map["level"]),
            (100000, 20, 15))
        for field in ("coins", "cash", "level"):
            self.assertIs(type(self.map[field]), int)

    def test_ranking_native_fields_and_refs(self):
        self.assertEqual(self.ranking["level"], 50)
        self.assertIs(type(self.ranking["level"]), int)
        self.assertEqual(self.ranking["cash"], 1)
        self.assertIs(type(self.ranking["cash"]), int)
        self.assertEqual(self.ranking["units"], {"1016": 1})
        self.assertEqual(self.ranking["unit_refs"], ["1016"])

    def test_expansion_rejects_bool_amount(self):
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_expansion(dict(self.layers["expansion_prices"][0],
                                          coins=True), 0, "mutated")

    def test_expansion_rejects_string_amount(self):
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_expansion(dict(self.layers["expansion_prices"][0],
                                          cash="20"), 0, "mutated")

    def test_expansion_rejects_negative_amount(self):
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_expansion(dict(self.layers["expansion_prices"][0],
                                          neighbors=-1), 0, "mutated")

    def test_town_rejects_string_level(self):
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_town(dict(self.layers["town_prices"][0],
                                     level="15"), 0, "mutated")

    def test_ranking_rejects_empty_units(self):
        mutated = dict(self.layers["level_ranking_reward"][0])
        mutated["units"] = {}
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_ranking(mutated, "mutated")

    def test_ranking_rejects_zero_quantity(self):
        mutated = dict(self.layers["level_ranking_reward"][0])
        key = next(iter(mutated["units"]))
        mutated["units"] = {key: 0}
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_ranking(mutated, "mutated")

    def test_ranking_rejects_string_cash(self):
        mutated = dict(self.layers["level_ranking_reward"][0])
        mutated["cash"] = "1"
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_ranking(mutated, "mutated")


class ClassificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        layers = builder.load_all(str(ROOT))
        cls.layers = layers
        cls.economy_section, cls.payloads = builder.build_package(
            str(ROOT), str(ROOT))

    def test_counts_match_verified_measurements(self):
        counts = self.economy_section["counts"]
        self.assertEqual(counts["stored_expansion_prices"], 98)
        self.assertEqual(counts["stored_town_prices"], 4)
        self.assertEqual(counts["stored_map_prices"], 4)
        self.assertEqual(counts["stored_ranking_rewards"], 50)
        self.assertEqual(counts["expansion_prices"], 98)
        self.assertEqual(counts["town_prices"], 4)
        self.assertEqual(counts["map_prices"], 4)
        self.assertEqual(counts["ranking_rewards"], 50)

    def test_schedules_fully_native(self):
        for entry in self.layers["expansion_prices"]:
            for field in ("coins", "cash", "neighbors", "inventory_qte"):
                self.assertIs(type(entry[field]), int)
        for key in ("town_prices", "map_prices"):
            for entry in self.layers[key]:
                for field in ("coins", "cash", "level"):
                    self.assertIs(type(entry[field]), int)
        for entry in self.layers["level_ranking_reward"]:
            self.assertIs(type(entry["level"]), int)
            self.assertIs(type(entry["cash"]), int)
            self.assertIsInstance(entry["units"], dict)

    def test_town_map_values_identical_but_files_separate(self):
        self.assertTrue(self.economy_section["counts"]["town_map_values_identical"])
        self.assertEqual(self.layers["town_prices"], self.layers["map_prices"])
        town = json.loads(self.payloads[builder.TOWN_FILE])
        maps = json.loads(self.payloads[builder.MAP_FILE])
        self.assertEqual([item["kind"] for item in town],
                         ["town_price"] * 4)
        self.assertEqual([item["kind"] for item in maps],
                         ["map_price"] * 4)
        self.assertEqual([item["legacy_id"] for item in town],
                         [item["legacy_id"] for item in maps])

    def test_ranking_levels_cover_50_to_1(self):
        ranking = json.loads(self.payloads[builder.RANKING_FILE])
        self.assertEqual(sorted(item["level"] for item in ranking),
                         list(range(1, 51)))
        self.assertEqual(self.economy_section["counts"]["ranking_level_min"], 1)
        self.assertEqual(self.economy_section["counts"]["ranking_level_max"], 50)
        self.assertEqual(self.economy_section["counts"]["ranking_cash_values"], [1])

    def test_ranking_units_resolve_against_items(self):
        union = self.layers["items_id_set"]
        self.assertEqual(len(union), 900)
        ranking = json.loads(self.payloads[builder.RANKING_FILE])
        for item in ranking:
            for key in item["unit_refs"]:
                self.assertIn(key, union)
            self.assertEqual(item["unit_refs"], sorted(item["units"].keys()))

    def test_no_patch_targets_economy_content(self):
        self.assertEqual(self.economy_section["inputs"]["economy_patch_targets"],
                         "none")
        self.assertEqual(self.economy_section["inputs"]["patch_order"],
                         ["atom_fusion_item", "unit_patch",
                          "atom_fusion_items_data", "atom_fusion_powerup",
                          "targets"])

    def test_envelope_fields_present(self):
        expansion = json.loads(self.payloads[builder.EXPANSION_FILE])
        for position, item in enumerate(expansion):
            for field in ("legacy_id", "kind", "source_file",
                          "source_layer", "content_version"):
                self.assertIn(field, item)
            self.assertEqual(item["kind"], "expansion_price")
            self.assertEqual(item["source_layer"], "stored")
            self.assertEqual(item["source_file"], "config/main.json")
            self.assertEqual(item["legacy_id"], str(position))
            self.assertEqual(item["position"], position)
            self.assertEqual(item["content_version"],
                             self.economy_section["content_fingerprint"])
        ranking = json.loads(self.payloads[builder.RANKING_FILE])
        for item in ranking:
            self.assertEqual(item["kind"], "level_ranking_reward")
            self.assertEqual(item["legacy_id"], str(item["level"]))
            self.assertEqual(item["unit_refs"], sorted(item["units"].keys()))

    def test_legacy_id_forms(self):
        expansion = json.loads(self.payloads[builder.EXPANSION_FILE])
        self.assertEqual([item["legacy_id"] for item in expansion],
                         [str(position) for position in range(98)])
        town = json.loads(self.payloads[builder.TOWN_FILE])
        self.assertEqual([item["legacy_id"] for item in town],
                         ["0", "1", "2", "3"])
        maps = json.loads(self.payloads[builder.MAP_FILE])
        self.assertEqual([item["legacy_id"] for item in maps],
                         ["0", "1", "2", "3"])
        ranking = json.loads(self.payloads[builder.RANKING_FILE])
        self.assertEqual([item["legacy_id"] for item in ranking],
                         [str(entry["level"]) for entry in
                          self.layers["level_ranking_reward"]])

    def test_schedule_order_matches_stored(self):
        expansion = json.loads(self.payloads[builder.EXPANSION_FILE])
        self.assertEqual([(item["coins"], item["cash"], item["neighbors"],
                           item["inventory_qte"]) for item in expansion],
                         [(entry["coins"], entry["cash"], entry["neighbors"],
                           entry["inventory_qte"]) for entry in
                          self.layers["expansion_prices"]])
        town = json.loads(self.payloads[builder.TOWN_FILE])
        self.assertEqual([(item["coins"], item["cash"], item["level"])
                          for item in town],
                         [(entry["coins"], entry["cash"], entry["level"])
                          for entry in self.layers["town_prices"]])


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
        self.assertEqual(report["counts"]["expansion_prices"], 98)
        self.assertEqual(report["counts"]["town_prices"], 4)
        self.assertEqual(report["counts"]["map_prices"], 4)
        self.assertEqual(report["counts"]["ranking_rewards"], 50)

    def test_negative_expansion_amount_exit_1(self):
        entries = load_work_schedule(self.work, "expansion_prices")
        entries[0]["coins"] = -1
        save_work_schedule(self.work, "expansion_prices", entries)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("coins", " ".join(json.loads(stdout)["problems"]))

    def test_missing_town_field_exit_1(self):
        entries = load_work_schedule(self.work, "town_prices")
        del entries[0]["level"]
        save_work_schedule(self.work, "town_prices", entries)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("missing", " ".join(json.loads(stdout)["problems"]))

    def test_missing_map_field_exit_1(self):
        entries = load_work_schedule(self.work, "map_prices")
        del entries[0]["cash"]
        save_work_schedule(self.work, "map_prices", entries)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("missing", " ".join(json.loads(stdout)["problems"]))

    def test_ranking_gap_exit_1(self):
        entries = load_work_schedule(self.work, "level_ranking_reward")
        entries[0]["level"] = 51
        save_work_schedule(self.work, "level_ranking_reward", entries)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("50..1", " ".join(json.loads(stdout)["problems"]))

    def test_duplicate_ranking_level_exit_1(self):
        entries = load_work_schedule(self.work, "level_ranking_reward")
        entries[0]["level"] = entries[1]["level"]
        save_work_schedule(self.work, "level_ranking_reward", entries)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("duplicate", " ".join(json.loads(stdout)["problems"]))

    def test_unresolvable_ranking_reference_exit_1(self):
        entries = load_work_schedule(self.work, "level_ranking_reward")
        key = next(iter(entries[0]["units"]))
        entries[0]["units"] = {"no_such_item_xyz": entries[0]["units"][key]}
        save_work_schedule(self.work, "level_ranking_reward", entries)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("unresolvable",
                      " ".join(json.loads(stdout)["problems"]))

    def test_missing_ranking_field_exit_1(self):
        entries = load_work_schedule(self.work, "level_ranking_reward")
        del entries[0]["units"]
        save_work_schedule(self.work, "level_ranking_reward", entries)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("missing", " ".join(json.loads(stdout)["problems"]))

    def test_failure_writes_nothing(self):
        before_manifest = (self.work / builder.MANIFEST_FILE).read_bytes()
        entries = load_work_schedule(self.work, "town_prices")
        del entries[0]["level"]
        save_work_schedule(self.work, "town_prices", entries)
        code, _, _ = self.build()
        self.assertEqual(code, 1)
        for name in EXPECTED_WRITES:
            if name == "packages/game-content/manifest.json":
                continue
            self.assertFalse((self.work / name).exists(), name)
        self.assertEqual((self.work / builder.MANIFEST_FILE).read_bytes(),
                         before_manifest)

    def test_economy_patch_target_exit_2(self):
        patch = self.work / "config" / "patch" / "targets.json"
        operations = json.loads(patch.read_text(encoding="utf-8"))
        operations.append({"op": "add", "path": "/town_prices/-", "value": {}})
        patch.write_text(json.dumps(operations), encoding="utf-8")
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("economy-schedule content", stderr)

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
         / "buildings.json").unlink()
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("normalized items", stderr)


class TraceabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _economy_section, payloads = builder.build_package(str(ROOT), str(ROOT))
        cls.expansion_schema = json.loads(
            (ROOT / builder.EXPANSION_SCHEMA_FILE).read_text(encoding="utf-8"))
        cls.town_schema = json.loads(
            (ROOT / builder.TOWN_SCHEMA_FILE).read_text(encoding="utf-8"))
        cls.map_schema = json.loads(
            (ROOT / builder.MAP_SCHEMA_FILE).read_text(encoding="utf-8"))
        cls.ranking_schema = json.loads(
            (ROOT / builder.RANKING_SCHEMA_FILE).read_text(encoding="utf-8"))
        cls.expansion = json.loads(payloads[builder.EXPANSION_FILE])[0]
        cls.town = json.loads(payloads[builder.TOWN_FILE])[0]
        cls.map = json.loads(payloads[builder.MAP_FILE])[0]
        cls.ranking = json.loads(payloads[builder.RANKING_FILE])[0]

    def schemas(self):
        return (("expansion_price", self.expansion_schema, self.expansion,
                 "expansion_price"),
                ("town_price", self.town_schema, self.town, "town_price"),
                ("map_price", self.map_schema, self.map, "map_price"),
                ("level_ranking_reward", self.ranking_schema, self.ranking,
                 "level_ranking_reward"))

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
        expansion_cases = [("position", "0"), ("coins", "0"), ("cash", 20.5),
                           ("neighbors", "0"), ("inventory_qte", "0")]
        for field, bad in expansion_cases:
            mutated = dict(self.expansion)
            mutated[field] = bad
            problems = builder.validate_against_schema(
                mutated, self.expansion_schema,
                "expansion_price " + self.expansion["legacy_id"])
            self.assertTrue(problems,
                            "no type check for expansion_price.%s" % (field,))
        town_cases = [("position", "0"), ("coins", "100000"),
                      ("cash", "20"), ("level", "15")]
        for field, bad in town_cases:
            mutated = dict(self.town)
            mutated[field] = bad
            problems = builder.validate_against_schema(
                mutated, self.town_schema,
                "town_price " + self.town["legacy_id"])
            self.assertTrue(problems,
                            "no type check for town_price.%s" % (field,))
        ranking_cases = [("level", "50"), ("cash", "1"), ("units", []),
                         ("unit_refs", "1016")]
        for field, bad in ranking_cases:
            mutated = dict(self.ranking)
            mutated[field] = bad
            problems = builder.validate_against_schema(
                mutated, self.ranking_schema,
                "level_ranking_reward " + self.ranking["legacy_id"])
            self.assertTrue(problems,
                            "no type check for level_ranking_reward.%s"
                            % (field,))

    def test_minimum_and_size_gates_enforced(self):
        mutated = dict(self.expansion)
        mutated["coins"] = -1
        self.assertTrue(builder.validate_against_schema(
            mutated, self.expansion_schema, "expansion_price"))
        mutated = dict(self.town)
        mutated["level"] = -1
        self.assertTrue(builder.validate_against_schema(
            mutated, self.town_schema, "town_price"))
        mutated = dict(self.ranking)
        mutated["unit_refs"] = []
        problems = builder.validate_against_schema(
            mutated, self.ranking_schema, "level_ranking_reward")
        self.assertTrue(any("minItems" in problem for problem in problems))
        mutated = dict(self.ranking)
        mutated["unit_refs"] = [1016]
        problems = builder.validate_against_schema(
            mutated, self.ranking_schema, "level_ranking_reward")
        self.assertTrue(problems)

    def test_kind_const_and_no_extra_properties(self):
        for schema, item, label in (
                (self.expansion_schema, self.expansion, "expansion_price"),
                (self.town_schema, self.town, "town_price"),
                (self.map_schema, self.map, "map_price"),
                (self.ranking_schema, self.ranking, "level_ranking_reward")):
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
        _economy_section, payloads = builder.build_package(str(ROOT), str(ROOT))
        expansion = json.loads(payloads[builder.EXPANSION_FILE])
        town = json.loads(payloads[builder.TOWN_FILE])
        maps = json.loads(payloads[builder.MAP_FILE])
        ranking = json.loads(payloads[builder.RANKING_FILE])
        problems = builder.check_round_trip(expansion, town, maps, ranking,
                                            layers["expansion_prices"],
                                            layers["town_prices"],
                                            layers["map_prices"],
                                            layers["level_ranking_reward"])
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
            self.assertIn("economy", manifest)
            economy_section = manifest["economy"]
            self.assertEqual(economy_section["result"], "success")
            self.assertEqual(economy_section["policy"], builder.POLICY)
            self.assertEqual(economy_section["coercion_ruleset"],
                             builder.COERCION_RULESET_VERSION)
            counts = economy_section["counts"]
            expansion = read_work_json(
                work, "packages/game-content/normalized/expansion_prices.json")
            town = read_work_json(
                work, "packages/game-content/normalized/town_prices.json")
            maps = read_work_json(
                work, "packages/game-content/normalized/map_prices.json")
            ranking = read_work_json(
                work, "packages/game-content/normalized/level_ranking_reward.json")
            self.assertEqual(len(expansion), counts["expansion_prices"])
            self.assertEqual(len(town), counts["town_prices"])
            self.assertEqual(len(maps), counts["map_prices"])
            self.assertEqual(len(ranking), counts["ranking_rewards"])
            self.assertEqual(counts["stored_expansion_prices"],
                             counts["expansion_prices"])
            self.assertEqual(counts["stored_town_prices"], counts["town_prices"])
            self.assertEqual(counts["stored_map_prices"], counts["map_prices"])
            self.assertEqual(counts["stored_ranking_rewards"],
                             counts["ranking_rewards"])
            self.assertEqual(economy_section["content_fingerprint"],
                             builder.fingerprint_inputs(
                                 builder.load_all(str(work))))
            self.assertEqual(economy_section["inputs"]["items_reference_edge"]["union_legacy_ids"],
                             900)
            by_file = {entry["file"]: entry
                       for entry in economy_section["outputs"]}
            self.assertEqual(set(by_file),
                             set(EXPECTED_WRITES)
                             - {"packages/game-content/manifest.json"})
            for name in ("packages/game-content/normalized/expansion_prices.json",
                         "packages/game-content/normalized/town_prices.json",
                         "packages/game-content/normalized/map_prices.json",
                         "packages/game-content/normalized/level_ranking_reward.json"):
                data = (work / name).read_bytes()
                self.assertEqual(by_file[name]["bytes"], len(data), name)
                self.assertEqual(by_file[name]["sha256"],
                                 hashlib.sha256(data).hexdigest(), name)
            self.assertTrue(economy_section["notes"])
            # Items, quests, and tables keys survive the economy merge untouched.
            self.assertEqual(manifest["policy"], "items-normalization-v1")
            self.assertEqual(manifest["counts"]["loaded_items"], 900)
            self.assertEqual(manifest["quests"]["policy"],
                             "quest-normalization-v1")
            self.assertEqual(manifest["quests"]["counts"]["quests"], 91)
            self.assertEqual(manifest["tables"]["policy"],
                             "tables-normalization-v1")
            self.assertEqual(manifest["tables"]["counts"]["magics"], 10)
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
                             {"packages/game-content/normalized/expansion_prices.json",
                              "packages/game-content/normalized/town_prices.json",
                              "packages/game-content/normalized/map_prices.json",
                              "packages/game-content/normalized/level_ranking_reward.json"})
            for path, payload in before.items():
                if path == "packages/game-content/manifest.json":
                    continue
                self.assertEqual(after[path], payload, path)
        finally:
            temporary.cleanup()

    def test_failure_writes_nothing_and_inputs_unchanged(self):
        temporary, work = make_work_tree()
        try:
            entries = load_work_schedule(work, "town_prices")
            del entries[0]["level"]
            save_work_schedule(work, "town_prices", entries)
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
                  / "build_economy.py").read_text(encoding="utf-8")
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
