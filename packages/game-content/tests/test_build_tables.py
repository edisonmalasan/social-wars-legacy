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

import build_tables as builder

EXPECTED_READS = frozenset([
    "config/main.json",
    "config/patch/patches.txt",
    "config/patch/atom_fusion_item.json",
    "config/patch/unit_patch.json",
    "config/patch/atom_fusion_items_data.json",
    "config/patch/atom_fusion_powerup.json",
    "config/patch/targets.json",
    "mods/mods.txt",
    "packages/game-content/schemas/magic.schema.json",
    "packages/game-content/schemas/level.schema.json",
    "packages/game-content/schemas/sound.schema.json",
    "packages/game-content/manifest.json",
])

EXPECTED_WRITES = frozenset([
    "packages/game-content/normalized/magics.json",
    "packages/game-content/normalized/levels.json",
    "packages/game-content/normalized/sounds.json",
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
    shutil.copy2(ROOT / "packages" / "game-content" / "tools" / "build_tables.py",
                 work / "packages" / "game-content" / "tools" / "build_tables.py")
    (work / "packages" / "game-content" / "schemas").mkdir(parents=True)
    for name in ("magic.schema.json", "level.schema.json", "sound.schema.json"):
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


class PredicateTests(unittest.TestCase):
    def test_numeric_grammar_matches_survey(self):
        self.assertEqual(builder.NUMERIC_GRAMMAR,
                         r"[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)"
                         r"(?:[eE][+-]?[0-9]+)?")

    def test_numeric_accepts_plain_signed_and_exponent(self):
        for text in ("0", "1", "007", "5", "3.14", ".7", "1e3"):
            self.assertTrue(builder.is_string_encoded_number(text),
                            "should be numeric: %r" % (text,))

    def test_numeric_rejects_words_and_blanks(self):
        for text in ("", "Test", "tech_airstrike", "-", " 12", "12 "):
            self.assertFalse(builder.is_string_encoded_number(text),
                             "should not be numeric: %r" % (text,))

    def test_embedded_json_accepts_arrays_and_numbers(self):
        for text in ("[5,7,9]", "[25,30,35]", "35", "1"):
            self.assertTrue(builder.is_embedded_json_string(text),
                            "should be embedded json: %r" % (text,))
        self.assertFalse(builder.is_embedded_json_string(""))

    def test_embedded_json_rejects_plain_words(self):
        for text in ("AirStrike", "tech_airstrike", "{broken"):
            self.assertFalse(builder.is_embedded_json_string(text),
                             "should not be embedded json: %r" % (text,))

    def test_coerce_number_integral_becomes_int(self):
        self.assertEqual(builder.coerce_number_text("35", "probe"), 35)
        self.assertIs(type(builder.coerce_number_text("007", "probe")), int)
        self.assertEqual(builder.coerce_number_text("1", "probe"), 1)

    def test_coerce_number_rejects_non_numeric(self):
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_number_text("AirStrike", "probe")


class CoercionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        layers = builder.load_all(str(ROOT))
        cls.magics = layers["magics"]
        cls.levels = layers["levels"]
        cls.sounds = layers["sounds"]
        by_magic = {entry["id"]: entry for entry in layers["magics"]}
        cls.first_magic = builder.coerce_magic(by_magic[1], "magic id 1")
        cls.first_level = builder.coerce_level(layers["levels"][0], 0,
                                               "level index 0")
        by_sound = {entry["id"]: entry for entry in layers["sounds"]}
        cls.first_sound = builder.coerce_sound(by_sound["1"],
                                               "sound id '1'")

    def test_magic_native_fields_kept_verbatim(self):
        self.assertEqual(self.first_magic["id"], 1)
        self.assertIs(type(self.first_magic["id"]), int)
        self.assertEqual(self.first_magic["mana"], 8)
        self.assertEqual(self.first_magic["level"], 38)
        self.assertEqual(self.first_magic["gold"], 30000)
        self.assertEqual(self.first_magic["cash"], 50)
        self.assertEqual(self.first_magic["target"], 2)
        for field in ("mana", "level", "gold", "cash", "target"):
            self.assertIs(type(self.first_magic[field]), int)

    def test_magic_area_coerces_to_int_array(self):
        self.assertEqual(self.first_magic["area"], [5, 7, 9])
        for value in self.first_magic["area"]:
            self.assertIs(type(value), int)

    def test_magic_asset_strings_verbatim(self):
        self.assertEqual(self.first_magic["name"], "AirStrike")
        self.assertEqual(self.first_magic["img_name"], "tech_airstrike")
        self.assertIsInstance(self.first_magic["description"], str)

    def test_magic_rejects_string_encoded_id(self):
        mutated = dict(self.magics[0])
        mutated["id"] = str(mutated["id"])
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_magic(mutated, "mutated")

    def test_magic_rejects_negative_amount(self):
        mutated = dict(self.magics[0])
        mutated["mana"] = -1
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_magic(mutated, "mutated")

    def test_magic_rejects_broken_area(self):
        mutated = dict(self.magics[0])
        mutated["area"] = "[5,seven,9]"
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_magic(mutated, "mutated")

    def test_level_native_fields_kept_verbatim(self):
        self.assertEqual(self.first_level["level_index"], 0)
        self.assertEqual(self.first_level["name"], "Slave")
        self.assertEqual(self.first_level["exp_required"], 0)
        self.assertIs(type(self.first_level["exp_required"]), int)
        self.assertEqual(self.first_level["reward_type"], "s")
        self.assertEqual(self.first_level["reward_amount"], 50)
        self.assertIs(type(self.first_level["reward_amount"]), int)

    def test_level_rejects_negative_xp(self):
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_level(dict(self.levels[0], exp_required=-1), 0,
                                 "mutated")

    def test_level_rejects_string_xp(self):
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_level(dict(self.levels[0], exp_required="40"), 0,
                                 "mutated")

    def test_sound_id_and_params_coerce_to_int(self):
        self.assertEqual(self.first_sound["id"], 1)
        self.assertIs(type(self.first_sound["id"]), int)
        self.assertEqual(self.first_sound["loops"], 1)
        self.assertEqual(self.first_sound["max"], 5)
        self.assertEqual(self.first_sound["preload"], 0)
        for field in ("loops", "max", "preload"):
            self.assertIs(type(self.first_sound[field]), int)

    def test_sound_asset_strings_verbatim(self):
        self.assertEqual(self.first_sound["file"], "explo1")
        self.assertEqual(self.first_sound["description"], "Test")

    def test_sound_rejects_non_integral_loops(self):
        mutated = dict(self.sounds[0])
        mutated["loops"] = "1.5"
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_sound(mutated, "mutated")

    def test_sound_rejects_negative_preload(self):
        mutated = dict(self.sounds[0])
        mutated["preload"] = "-1"
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_sound(mutated, "mutated")


class ClassificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        layers = builder.load_all(str(ROOT))
        cls.layers = layers
        cls.tables_section, cls.payloads = builder.build_package(
            str(ROOT), str(ROOT))

    def test_counts_match_verified_measurements(self):
        counts = self.tables_section["counts"]
        self.assertEqual(counts["stored_magics"], 10)
        self.assertEqual(counts["stored_levels"], 100)
        self.assertEqual(counts["stored_sounds"], 139)
        self.assertEqual(counts["magics"], 10)
        self.assertEqual(counts["levels"], 100)
        self.assertEqual(counts["sounds"], 139)

    def test_magics_native_ids_and_embedded_area(self):
        for entry in self.layers["magics"]:
            self.assertIs(type(entry["id"]), int)
            for field in ("mana", "level", "gold", "cash", "target"):
                self.assertIs(type(entry[field]), int)
            self.assertIsInstance(entry["area"], str)
            self.assertTrue(builder.is_embedded_json_string(entry["area"]))
        identifiers = [entry["id"] for entry in self.layers["magics"]]
        self.assertEqual(len(set(identifiers)), 10)

    def test_levels_fully_native_and_positional(self):
        counts = self.tables_section["counts"]
        self.assertEqual(counts["exp_min"], 0)
        self.assertEqual(counts["exp_max"], 2016089205)
        self.assertTrue(counts["exp_monotonic_nondecreasing"])
        for entry in self.layers["levels"]:
            self.assertIsInstance(entry["name"], str)
            self.assertIs(type(entry["exp_required"]), int)
            self.assertIsInstance(entry["reward_type"], str)
            self.assertIs(type(entry["reward_amount"]), int)
            self.assertNotIn("id", entry)

    def test_sounds_string_encoded_source_shape(self):
        for entry in self.layers["sounds"]:
            self.assertIsInstance(entry["id"], str)
            self.assertIsInstance(entry["loops"], str)
            self.assertIsInstance(entry["max"], str)
            self.assertIsInstance(entry["preload"], str)
            self.assertIsInstance(entry["file"], str)
            self.assertIsInstance(entry["description"], str)
        identifiers = [entry["id"] for entry in self.layers["sounds"]]
        self.assertEqual(len(set(identifiers)), 139)

    def test_no_patch_targets_tables_content(self):
        self.assertEqual(self.tables_section["inputs"]["tables_patch_targets"],
                         "none")
        self.assertEqual(self.tables_section["inputs"]["patch_order"],
                         ["atom_fusion_item", "unit_patch",
                          "atom_fusion_items_data", "atom_fusion_powerup",
                          "targets"])

    def test_envelope_fields_present(self):
        magics = json.loads(self.payloads[builder.MAGICS_FILE])
        for item in magics:
            for field in ("legacy_id", "kind", "source_file",
                          "source_layer", "content_version"):
                self.assertIn(field, item)
            self.assertEqual(item["kind"], "magic")
            self.assertEqual(item["source_layer"], "stored")
            self.assertEqual(item["source_file"], "config/main.json")
            self.assertEqual(item["content_version"],
                             self.tables_section["content_fingerprint"])
            self.assertEqual(item["legacy_id"], str(item["id"]))
            self.assertEqual(item["area"], json.loads(
                [entry for entry in self.layers["magics"]
                 if entry["id"] == item["id"]][0]["area"]))
        levels = json.loads(self.payloads[builder.LEVELS_FILE])
        for position, item in enumerate(levels):
            self.assertEqual(item["kind"], "level")
            self.assertEqual(item["legacy_id"], str(position))
            self.assertEqual(item["level_index"], position)
            self.assertEqual(item["content_version"],
                             self.tables_section["content_fingerprint"])
        sounds = json.loads(self.payloads[builder.SOUNDS_FILE])
        for item in sounds:
            self.assertEqual(item["kind"], "sound")
            self.assertEqual(item["legacy_id"], str(item["id"]))
            self.assertEqual(item["content_version"],
                             self.tables_section["content_fingerprint"])

    def test_legacy_id_forms(self):
        magics = json.loads(self.payloads[builder.MAGICS_FILE])
        self.assertEqual({item["legacy_id"] for item in magics},
                         {str(entry["id"]) for entry in self.layers["magics"]})
        levels = json.loads(self.payloads[builder.LEVELS_FILE])
        self.assertEqual([item["legacy_id"] for item in levels],
                         [str(position)
                          for position in range(len(self.layers["levels"]))])
        sounds = json.loads(self.payloads[builder.SOUNDS_FILE])
        self.assertEqual([item["legacy_id"] for item in sounds],
                         [entry["id"] for entry in self.layers["sounds"]])

    def test_level_order_matches_stored_curve(self):
        levels = json.loads(self.payloads[builder.LEVELS_FILE])
        self.assertEqual([item["exp_required"] for item in levels],
                         [entry["exp_required"]
                          for entry in self.layers["levels"]])
        self.assertEqual([item["name"] for item in levels],
                         [entry["name"] for entry in self.layers["levels"]])


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
        self.assertEqual(report["counts"]["magics"], 10)
        self.assertEqual(report["counts"]["levels"], 100)
        self.assertEqual(report["counts"]["sounds"], 139)

    def test_duplicate_magic_id_exit_1_and_writes_nothing(self):
        magics = load_work_table(self.work, "magics")
        magics.append(dict(magics[0]))
        save_work_table(self.work, "magics", magics)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("duplicate", json.loads(stdout)["problems"][0])
        self.assertFalse((self.work / builder.MAGICS_FILE).exists())
        self.assertFalse((self.work / builder.LEVELS_FILE).exists())
        self.assertFalse((self.work / builder.SOUNDS_FILE).exists())

    def test_duplicate_sound_id_exit_1(self):
        sounds = load_work_table(self.work, "sounds")
        sounds.append(dict(sounds[0]))
        save_work_table(self.work, "sounds", sounds)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("duplicate", json.loads(stdout)["problems"][0])

    def test_negative_magic_amount_exit_1(self):
        magics = load_work_table(self.work, "magics")
        magics[0]["mana"] = -1
        save_work_table(self.work, "magics", magics)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("mana", " ".join(json.loads(stdout)["problems"]))

    def test_negative_sound_amount_exit_1(self):
        sounds = load_work_table(self.work, "sounds")
        sounds[0]["loops"] = "-1"
        save_work_table(self.work, "sounds", sounds)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("loops", " ".join(json.loads(stdout)["problems"]))

    def test_negative_xp_exit_1(self):
        levels = load_work_table(self.work, "levels")
        levels[0]["exp_required"] = -5
        save_work_table(self.work, "levels", levels)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("exp_required",
                      " ".join(json.loads(stdout)["problems"]))

    def test_missing_magic_field_exit_1(self):
        magics = load_work_table(self.work, "magics")
        del magics[0]["area"]
        save_work_table(self.work, "magics", magics)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("missing", " ".join(json.loads(stdout)["problems"]))

    def test_missing_level_field_exit_1(self):
        levels = load_work_table(self.work, "levels")
        del levels[0]["exp_required"]
        save_work_table(self.work, "levels", levels)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("missing", " ".join(json.loads(stdout)["problems"]))

    def test_missing_sound_field_exit_1(self):
        sounds = load_work_table(self.work, "sounds")
        del sounds[0]["loops"]
        save_work_table(self.work, "sounds", sounds)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("missing", " ".join(json.loads(stdout)["problems"]))

    def test_failure_writes_nothing(self):
        before_manifest = (self.work / builder.MANIFEST_FILE).read_bytes()
        magics = load_work_table(self.work, "magics")
        del magics[0]["area"]
        save_work_table(self.work, "magics", magics)
        code, _, _ = self.build()
        self.assertEqual(code, 1)
        self.assertFalse((self.work / builder.MAGICS_FILE).exists())
        self.assertFalse((self.work / builder.LEVELS_FILE).exists())
        self.assertFalse((self.work / builder.SOUNDS_FILE).exists())
        self.assertEqual((self.work / builder.MANIFEST_FILE).read_bytes(),
                         before_manifest)

    def test_tables_patch_target_exit_2(self):
        patch = self.work / "config" / "patch" / "targets.json"
        operations = json.loads(patch.read_text(encoding="utf-8"))
        operations.append({"op": "add", "path": "/sounds/-", "value": {}})
        patch.write_text(json.dumps(operations), encoding="utf-8")
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("reference-table content", stderr)

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
        _tables_section, payloads = builder.build_package(str(ROOT), str(ROOT))
        cls.magic_schema = json.loads(
            (ROOT / builder.MAGIC_SCHEMA_FILE).read_text(encoding="utf-8"))
        cls.level_schema = json.loads(
            (ROOT / builder.LEVEL_SCHEMA_FILE).read_text(encoding="utf-8"))
        cls.sound_schema = json.loads(
            (ROOT / builder.SOUND_SCHEMA_FILE).read_text(encoding="utf-8"))
        cls.magic = json.loads(payloads[builder.MAGICS_FILE])[0]
        cls.level = json.loads(payloads[builder.LEVELS_FILE])[0]
        cls.sound = json.loads(payloads[builder.SOUNDS_FILE])[0]

    def schemas(self):
        return (("magic", self.magic_schema, self.magic, "magic"),
                ("level", self.level_schema, self.level, "level"),
                ("sound", self.sound_schema, self.sound, "sound"))

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
        magic_cases = [("id", "1"), ("name", 5), ("mana", "8"),
                       ("area", "[5,7,9]"), ("img_name", 7),
                       ("target", "2")]
        for field, bad in magic_cases:
            mutated = dict(self.magic)
            mutated[field] = bad
            problems = builder.validate_against_schema(
                mutated, self.magic_schema, "magic " + self.magic["legacy_id"])
            self.assertTrue(problems,
                            "no type check for magic.%s" % (field,))
        level_cases = [("level_index", "0"), ("name", 5),
                       ("exp_required", "0"), ("reward_type", 3),
                       ("reward_amount", "50")]
        for field, bad in level_cases:
            mutated = dict(self.level)
            mutated[field] = bad
            problems = builder.validate_against_schema(
                mutated, self.level_schema, "level " + self.level["legacy_id"])
            self.assertTrue(problems,
                            "no type check for level.%s" % (field,))
        sound_cases = [("id", "1"), ("file", 5), ("loops", "1"),
                       ("max", "5"), ("preload", "0"), ("description", [])]
        for field, bad in sound_cases:
            mutated = dict(self.sound)
            mutated[field] = bad
            problems = builder.validate_against_schema(
                mutated, self.sound_schema,
                "sound " + self.sound["legacy_id"])
            self.assertTrue(problems,
                            "no type check for sound.%s" % (field,))

    def test_minimum_and_size_gates_enforced(self):
        mutated = dict(self.magic)
        mutated["mana"] = -1
        self.assertTrue(builder.validate_against_schema(
            mutated, self.magic_schema, "magic"))
        mutated = dict(self.magic)
        mutated["area"] = []
        self.assertTrue(builder.validate_against_schema(
            mutated, self.magic_schema, "magic"))
        mutated = dict(self.level)
        mutated["exp_required"] = -1
        self.assertTrue(builder.validate_against_schema(
            mutated, self.level_schema, "level"))
        mutated = dict(self.level)
        mutated["reward_type"] = "oil"
        problems = builder.validate_against_schema(
            mutated, self.level_schema, "level")
        self.assertTrue(any("enum mismatch" in problem for problem in problems))
        mutated = dict(self.sound)
        mutated["loops"] = -1
        self.assertTrue(builder.validate_against_schema(
            mutated, self.sound_schema, "sound"))

    def test_kind_const_and_no_extra_properties(self):
        for schema, item, label in (
                (self.magic_schema, self.magic, "magic"),
                (self.level_schema, self.level, "level"),
                (self.sound_schema, self.sound, "sound")):
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
        _tables_section, payloads = builder.build_package(str(ROOT), str(ROOT))
        magics = json.loads(payloads[builder.MAGICS_FILE])
        levels = json.loads(payloads[builder.LEVELS_FILE])
        sounds = json.loads(payloads[builder.SOUNDS_FILE])
        problems = builder.check_round_trip(magics, levels, sounds,
                                            layers["magics"],
                                            layers["levels"],
                                            layers["sounds"])
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
            self.assertIn("tables", manifest)
            tables_section = manifest["tables"]
            self.assertEqual(tables_section["result"], "success")
            self.assertEqual(tables_section["policy"], builder.POLICY)
            self.assertEqual(tables_section["coercion_ruleset"],
                             builder.COERCION_RULESET_VERSION)
            counts = tables_section["counts"]
            magics = read_work_json(
                work, "packages/game-content/normalized/magics.json")
            levels = read_work_json(
                work, "packages/game-content/normalized/levels.json")
            sounds = read_work_json(
                work, "packages/game-content/normalized/sounds.json")
            self.assertEqual(len(magics), counts["magics"])
            self.assertEqual(len(levels), counts["levels"])
            self.assertEqual(len(sounds), counts["sounds"])
            self.assertEqual(counts["stored_magics"], counts["magics"])
            self.assertEqual(counts["stored_levels"], counts["levels"])
            self.assertEqual(counts["stored_sounds"], counts["sounds"])
            self.assertEqual(tables_section["content_fingerprint"],
                             builder.fingerprint_inputs(
                                 builder.load_all(str(work))))
            by_file = {entry["file"]: entry
                       for entry in tables_section["outputs"]}
            self.assertEqual(set(by_file),
                             set(EXPECTED_WRITES)
                             - {"packages/game-content/manifest.json"})
            for name in ("packages/game-content/normalized/magics.json",
                         "packages/game-content/normalized/levels.json",
                         "packages/game-content/normalized/sounds.json"):
                data = (work / name).read_bytes()
                self.assertEqual(by_file[name]["bytes"], len(data), name)
                self.assertEqual(by_file[name]["sha256"],
                                 hashlib.sha256(data).hexdigest(), name)
            self.assertTrue(tables_section["notes"])
            # Items and quests keys survive the tables merge untouched.
            self.assertEqual(manifest["policy"], "items-normalization-v1")
            self.assertEqual(manifest["counts"]["loaded_items"], 900)
            self.assertEqual(manifest["quests"]["policy"],
                             "quest-normalization-v1")
            self.assertEqual(manifest["quests"]["counts"]["quests"], 91)
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
                             {"packages/game-content/normalized/magics.json",
                              "packages/game-content/normalized/levels.json",
                              "packages/game-content/normalized/sounds.json"})
            for path, payload in before.items():
                if path == "packages/game-content/manifest.json":
                    continue
                self.assertEqual(after[path], payload, path)
        finally:
            temporary.cleanup()

    def test_failure_writes_nothing_and_inputs_unchanged(self):
        temporary, work = make_work_tree()
        try:
            magics = load_work_table(work, "magics")
            del magics[0]["area"]
            save_work_table(work, "magics", magics)
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
                  / "build_tables.py").read_text(encoding="utf-8")
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
