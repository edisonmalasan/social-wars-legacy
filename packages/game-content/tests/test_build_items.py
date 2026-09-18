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

import build_items as builder

EXPECTED_READS = frozenset([
    "config/main.json",
    "config/patch/patches.txt",
    "config/patch/atom_fusion_item.json",
    "config/patch/unit_patch.json",
    "config/patch/atom_fusion_items_data.json",
    "config/patch/atom_fusion_powerup.json",
    "config/patch/targets.json",
    "mods/mods.txt",
    "packages/game-content/schemas/building.schema.json",
    "packages/game-content/schemas/unit.schema.json",
])

EXPECTED_WRITES = frozenset([
    "packages/game-content/normalized/buildings.json",
    "packages/game-content/normalized/units.json",
    "packages/game-content/normalized/specials.json",
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
    shutil.copy2(ROOT / "packages" / "game-content" / "tools" / "build_items.py",
                 work / "packages" / "game-content" / "tools" / "build_items.py")
    (work / "packages" / "game-content" / "schemas").mkdir(parents=True)
    for name in ("building.schema.json", "unit.schema.json"):
        shutil.copy2(ROOT / "packages" / "game-content" / "schemas" / name,
                     work / "packages" / "game-content" / "schemas" / name)
    return temporary, work


def read_work_json(work, relative):
    return json.loads((work / relative).read_text(encoding="utf-8"))


def write_work_json(work, relative, document):
    (work / relative).write_text(json.dumps(document), encoding="utf-8")


def load_work_items(work):
    return read_work_json(work, "config/main.json")["items"]


def save_work_items(work, items):
    document = read_work_json(work, "config/main.json")
    document["items"] = items
    write_work_json(work, "config/main.json", document)


class PredicateTests(unittest.TestCase):
    def test_numeric_grammar_matches_survey(self):
        self.assertEqual(builder.NUMERIC_GRAMMAR,
                         r"[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)"
                         r"(?:[eE][+-]?[0-9]+)?")

    def test_numeric_accepts_plain_signed_and_exponent(self):
        for text in ("0", "-1", "+8", "007", "14000", "3.14", ".7", "1e3"):
            self.assertTrue(builder.is_string_encoded_number(text),
                            "should be numeric: %r" % (text,))

    def test_numeric_rejects_words_blanks_and_dates(self):
        for text in ("", "HOUSING", "g", "-", "ft_ground", "2012-03-02",
                     "terreno", " 12", "12 "):
            self.assertFalse(builder.is_string_encoded_number(text),
                             "should not be numeric: %r" % (text,))

    def test_embedded_json_accepts_containers_quoted_null_and_numbers(self):
        for text in ('{"w":30}', '{"g":300, "o":600}', "null", "7", "14000",
                     '{"2":1, "17":2}', "", ):
            if text == "":
                self.assertFalse(builder.is_embedded_json_string(text))
            else:
                self.assertTrue(builder.is_embedded_json_string(text),
                                "should be embedded json: %r" % (text,))

    def test_embedded_json_rejects_plain_words(self):
        for text in ("HOUSING", "g", "-", "ft_ground", "terreno", "{broken"):
            self.assertFalse(builder.is_embedded_json_string(text),
                             "should not be embedded json: %r" % (text,))

    def test_coerce_number_integral_becomes_int(self):
        self.assertEqual(builder.coerce_number_text("47", "probe"), 47)
        self.assertIs(type(builder.coerce_number_text("47", "probe")), int)
        self.assertEqual(builder.coerce_number_text("007", "probe"), 7)

    def test_coerce_number_rejects_non_numeric(self):
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_number_text("HOUSING", "probe")


class CoercionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        layers = builder.load_all(str(ROOT))
        cls.items = layers["items"]
        by_id = {entry["id"]: entry for entry in layers["items"]}
        cls.house = builder.coerce_item(by_id["1"], "item id '1'")
        cls.market = builder.coerce_item(by_id["1002"], "item id '1002'")
        cls.special = builder.coerce_item(by_id["925"], "item id '925'")

    def test_house_costs_coerce_to_object(self):
        self.assertEqual(self.house["costs"], {"w": 30})
        self.assertEqual(self.house["upgrades_to"], 47)
        self.assertEqual(self.house["trains_ids"], -1)

    def test_multi_key_costs_preserved(self):
        self.assertEqual(self.market["costs"], {"g": 300, "o": 600})

    def test_meaningful_empty_strings_preserved(self):
        self.assertEqual(self.house["best_against"], "")
        self.assertEqual(self.house["group_type"], "HOUSING")

    def test_absence_empties_become_null(self):
        self.assertIsNone(self.house["premium_upgrade_costs"])
        self.assertIsNone(self.house["inventory_ids"])
        self.assertIsInstance(self.house["properties"], dict)

    def test_special_empty_properties_becomes_null(self):
        self.assertIsNone(self.special["properties"])
        self.assertEqual(self.special["group_type"], "")
        self.assertEqual(self.special["best_against"], "")

    def test_numeric_strings_become_integers(self):
        for field in ("in_store", "xp", "width", "life", "build_time"):
            self.assertIs(type(self.house[field]), int, field)

    def test_plain_strings_verbatim(self):
        self.assertEqual(self.house["name"], "House I")
        self.assertEqual(self.house["img_name"], "0001_house_1_m")
        self.assertEqual(self.house["race"], "-")
        self.assertEqual(self.house["type"], "b")

    def test_cost_type_dropped(self):
        self.assertNotIn("cost_type", self.house)

    def test_breeding_fields_coerce_where_patched(self):
        layers = builder.load_all(str(ROOT))
        bred = [entry for entry in layers["items"] if "breeding_order" in entry]
        self.assertEqual(len(bred), 300)
        body = builder.coerce_item(bred[0], "bred")
        self.assertIs(type(body["breeding_order"]), int)
        self.assertIs(type(body["sm_training_time"]), int)

    def test_flag_best_against_preserved_verbatim(self):
        layers = builder.load_all(str(ROOT))
        flagged = [entry for entry in layers["items"]
                   if entry["best_against"] == "ft_ground"]
        self.assertTrue(flagged)
        body = builder.coerce_item(flagged[0], "flagged")
        self.assertEqual(body["best_against"], "ft_ground")

class ClassificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        layers = builder.load_all(str(ROOT))
        cls.layers = layers
        cls.manifest, cls.payloads, _ = builder.build_package(
            str(ROOT), str(ROOT))

    def test_loaded_counts_match_verified_measurements(self):
        counts = self.manifest["counts"]
        self.assertEqual(counts["stored_items"], 778)
        self.assertEqual(counts["appended_items"], 122)
        self.assertEqual(counts["loaded_items"], 900)
        self.assertEqual(counts["buildings"], 470)
        self.assertEqual(counts["units"], 429)
        self.assertEqual(counts["specials"], 1)

    def test_stored_split_matches_census(self):
        stored_types = {}
        document = json.loads(
            (ROOT / "config" / "main.json").read_text(encoding="utf-8"))
        for entry in document["items"]:
            stored_types[entry["type"]] = stored_types.get(entry["type"], 0) + 1
        self.assertEqual(stored_types, {"b": 469, "u": 308, "l": 1})

    def test_appended_split_is_one_building_and_121_units(self):
        kinds = {}
        for info in self.manifest["inputs"]["patches"]:
            kinds[info["name"]] = info["appended_items"]
        self.assertEqual(kinds["atom_fusion_item"], 1)
        self.assertEqual(kinds["unit_patch"], 121)
        buildings = json.loads(self.payloads[builder.BUILDINGS_FILE])
        appended = [item for item in buildings
                    if item["source_layer"] != "stored"]
        self.assertEqual(len(appended), 1)
        self.assertEqual(appended[0]["legacy_id"], "302")
        units = json.loads(self.payloads[builder.UNITS_FILE])
        appended_units = [item for item in units
                          if item["source_layer"] != "stored"]
        self.assertEqual(len(appended_units), 121)

    def test_all_loaded_ids_distinct(self):
        identifiers = [entry["id"] for entry in self.layers["items"]]
        self.assertEqual(len(set(identifiers)), 900)

    def test_special_is_expandable_land_only(self):
        specials = json.loads(self.payloads[builder.SPECIALS_FILE])
        self.assertEqual(len(specials), 1)
        special = specials[0]
        self.assertEqual(special["legacy_id"], "925")
        self.assertEqual(special["kind"], "special")
        self.assertEqual(special["name"], "Expandable Land")
        self.assertEqual(special["type"], "l")
        self.assertEqual(special["special_note"], builder.SPECIAL_NOTE)

    def test_relation_and_breeding_measurements(self):
        counts = self.manifest["counts"]
        self.assertEqual(counts["upgrades_nontrivial"], 56)
        self.assertEqual(counts["trains_nondefault"], 130)
        self.assertEqual(counts["with_breeding_fields"], 300)

    def test_envelope_fields_present(self):
        buildings = json.loads(self.payloads[builder.BUILDINGS_FILE])
        for item in buildings[:5] + buildings[-5:]:
            for field in ("legacy_id", "kind", "source_file",
                          "source_layer", "content_version"):
                self.assertIn(field, item)
            self.assertEqual(item["kind"], "building")
            self.assertEqual(item["content_version"],
                             self.manifest["content_fingerprint"])


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
        self.assertEqual(report["counts"]["buildings"], 470)
        self.assertEqual(report["counts"]["units"], 429)
        self.assertEqual(report["counts"]["specials"], 1)

    def test_duplicate_id_exit_1_and_writes_nothing(self):
        items = load_work_items(self.work)
        items.append(dict(items[0]))
        save_work_items(self.work, items)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("duplicate", json.loads(stdout)["problems"][0])
        self.assertFalse((self.work / builder.BUILDINGS_FILE).exists())
        self.assertFalse((self.work / builder.MANIFEST_FILE).exists())

    def test_unresolvable_upgrades_exit_1(self):
        items = load_work_items(self.work)
        items[0]["upgrades_to"] = "99999"
        save_work_items(self.work, items)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("unresolvable",
                      " ".join(json.loads(stdout)["problems"]))

    def test_bad_cost_key_exit_1(self):
        items = load_work_items(self.work)
        items[0]["costs"] = '{"x": 5}'
        save_work_items(self.work, items)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("cost key", " ".join(json.loads(stdout)["problems"]))

    def test_negative_cost_amount_exit_1(self):
        items = load_work_items(self.work)
        items[0]["costs"] = '{"w": -5}'
        save_work_items(self.work, items)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("cost amount", " ".join(json.loads(stdout)["problems"]))

    def test_missing_field_exit_1(self):
        items = load_work_items(self.work)
        del items[0]["name"]
        save_work_items(self.work, items)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("missing", " ".join(json.loads(stdout)["problems"]))

    def test_unknown_type_exit_1(self):
        items = load_work_items(self.work)
        items[0]["type"] = "z"
        save_work_items(self.work, items)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("unknown type", " ".join(json.loads(stdout)["problems"]))

    def test_unsupported_patch_op_exit_2(self):
        patch = self.work / "config" / "patch" / "targets.json"
        operations = json.loads(patch.read_text(encoding="utf-8"))
        operations[0]["op"] = "move"
        patch.write_text(json.dumps(operations), encoding="utf-8")
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("unsupported patch operation", stderr)

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
        manifest, payloads, _ = builder.build_package(str(ROOT), str(ROOT))
        cls.building_schema = json.loads(
            (ROOT / builder.BUILDING_SCHEMA_FILE).read_text(encoding="utf-8"))
        cls.unit_schema = json.loads(
            (ROOT / builder.UNIT_SCHEMA_FILE).read_text(encoding="utf-8"))
        cls.building = json.loads(payloads[builder.BUILDINGS_FILE])[0]
        cls.unit = json.loads(payloads[builder.UNITS_FILE])[0]

    def schemas(self):
        return (("building", self.building_schema, self.building, "building"),
                ("unit", self.unit_schema, self.unit, "unit"))

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
        cases = [("xp", "3"), ("name", 5), ("costs", [1]),
                 ("inventory_ids", []), ("best_against", {}),
                 ("premium_upgrade_costs", "x")]
        for kind, schema, item, label in self.schemas():
            for field, bad in cases:
                mutated = dict(item)
                mutated[field] = bad
                problems = builder.validate_against_schema(
                    mutated, schema, label + " " + item["legacy_id"])
                self.assertTrue(problems,
                                "no type check for %s.%s" % (kind, field))

    def test_cost_key_set_and_minimum_enforced(self):
        mutated = dict(self.building)
        mutated["costs"] = {"x": 1}
        self.assertTrue(builder.validate_against_schema(
            mutated, self.building_schema, "building"))
        mutated["costs"] = {"w": -1}
        self.assertTrue(builder.validate_against_schema(
            mutated, self.building_schema, "building"))

    def test_kind_const_and_no_extra_properties(self):
        mutated = dict(self.building)
        mutated["kind"] = "unit"
        self.assertTrue(builder.validate_against_schema(
            mutated, self.building_schema, "building"))
        mutated = dict(self.building)
        mutated["invented_field"] = 1
        problems = builder.validate_against_schema(
            mutated, self.building_schema, "building")
        self.assertTrue(any("additional property" in problem
                            for problem in problems))

    def test_both_schemas_share_shape_except_kind(self):
        self.assertEqual(self.building_schema["required"],
                         self.unit_schema["required"])
        skip = ("$id", "title", "description")
        mine = {key: value for key, value in self.building_schema.items()
                if key not in skip}
        theirs = {key: value for key, value in self.unit_schema.items()
                  if key not in skip}
        # kind const and the stored-type wording differ by design.
        mine["properties"] = {key: value for key, value in
                              mine["properties"].items()
                              if key not in ("kind", "type")}
        theirs["properties"] = {key: value for key, value in
                                theirs["properties"].items()
                                if key not in ("kind", "type")}
        self.assertEqual(mine, theirs)
        mine_kind = self.building_schema["properties"]["kind"]
        theirs_kind = self.unit_schema["properties"]["kind"]
        self.assertEqual(mine_kind["const"], "building")
        self.assertEqual(theirs_kind["const"], "unit")
        self.assertIn("b", self.building_schema["properties"]["type"]
                      ["description"])
        self.assertIn("u", self.unit_schema["properties"]["type"]
                      ["description"])


class RoundTripTests(unittest.TestCase):
    def test_round_trip_clean_on_real_content(self):
        layers = builder.load_all(str(ROOT))
        manifest, payloads, _ = builder.build_package(str(ROOT), str(ROOT))
        bodies = (json.loads(payloads[builder.BUILDINGS_FILE])
                  + json.loads(payloads[builder.UNITS_FILE])
                  + json.loads(payloads[builder.SPECIALS_FILE]))
        # Re-emission order is loaded order; bodies arrive grouped, so sort
        # both sides by loaded position for the comparison.
        order = {entry["id"]: index for index, entry
                 in enumerate(layers["items"])}
        bodies.sort(key=lambda item: order[item["legacy_id"]])
        problems = builder.check_round_trip(bodies, layers["items"])
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
            self.assertEqual(manifest["result"], "success")
            self.assertEqual(manifest["coercion_ruleset"],
                             builder.COERCION_RULESET_VERSION)
            counts = manifest["counts"]
            for name, key in (("normalized/buildings.json", "buildings"),
                              ("normalized/units.json", "units"),
                              ("normalized/specials.json", "specials")):
                entries = read_work_json(
                    work, "packages/game-content/" + name)
                self.assertEqual(len(entries), counts[key], name)
            self.assertEqual(counts["loaded_items"],
                             counts["buildings"] + counts["units"]
                             + counts["specials"])
            self.assertEqual(manifest["layering"]["order"],
                             manifest["inputs"]["patch_list"]["order"])
            self.assertEqual(manifest["content_fingerprint"],
                             builder.fingerprint_inputs(
                                 work, builder.load_all(str(work))))
            by_file = {entry["file"]: entry
                       for entry in manifest["outputs"]}
            # The manifest digests the three normalized files; it cannot
            # digest itself, so it is checked separately below.
            self.assertEqual(set(by_file), set(EXPECTED_WRITES)
                             - {"packages/game-content/manifest.json"})
            for name in EXPECTED_WRITES:
                data = (work / name).read_bytes()
                if name == "packages/game-content/manifest.json":
                    reread = json.loads(data.decode("utf-8"))
                    self.assertEqual(reread["result"], "success")
                    self.assertEqual(reread["counts"], counts)
                    continue
                self.assertEqual(by_file[name]["bytes"], len(data), name)
                self.assertEqual(by_file[name]["sha256"],
                                 hashlib.sha256(data).hexdigest(), name)
            self.assertTrue(manifest["notes"])
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
            self.assertEqual(new_files, EXPECTED_WRITES)
            for path, payload in before.items():
                self.assertEqual(after[path], payload, path)
        finally:
            temporary.cleanup()

    def test_failure_writes_nothing_and_inputs_unchanged(self):
        temporary, work = make_work_tree()
        try:
            items = load_work_items(work)
            items[0]["upgrades_to"] = "99999"
            save_work_items(work, items)
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
                  / "build_items.py").read_text(encoding="utf-8")
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



