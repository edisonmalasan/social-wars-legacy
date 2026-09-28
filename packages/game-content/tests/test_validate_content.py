import contextlib
import copy
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "packages" / "game-content" / "tools"))

import validate_content as validator  # noqa: E402

PACKAGE = ROOT / "packages" / "game-content"
TOOL = PACKAGE / "tools" / "validate_content.py"
NORMALIZED = PACKAGE / "normalized"
SCHEMAS = PACKAGE / "schemas"

FORBIDDEN_SOURCE_TOKENS = (
    "config/", "mods/", "saves/", "get_game_config", "flask",
    "requests", "socket", "urllib", "http://", "https://",
    "subprocess", "webbrowser", "playwright", "ruffle", ".swf",
)


def run_main(repo_root, argv=None):
    out, err = io.StringIO(), io.StringIO()
    if argv is None:
        argv = ["--repo-root", str(repo_root)]
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = validator.main(argv)
    return code, out.getvalue(), err.getvalue()


def run_cli(repo_root):
    completed = subprocess.run(
        [sys.executable, "-B", str(TOOL), "--repo-root", str(repo_root)],
        cwd=str(ROOT), capture_output=True, timeout=300)
    return completed.returncode, completed.stdout, completed.stderr


def snapshot(directory):
    return {
        str(path.relative_to(directory)).replace("\\", "/"):
            hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*")) if path.is_file()
    }


def copy_repo(temp_root):
    destination = Path(temp_root) / "packages" / "game-content"
    shutil.copytree(PACKAGE, destination)
    return Path(temp_root)


def normalized_path(repo_root, name):
    return Path(repo_root) / "packages" / "game-content" / "normalized" / name


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path, value):
    Path(path).write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8")


def mutate(repo_root, name, change):
    path = normalized_path(repo_root, name)
    entries = load_json(path)
    change(entries)
    save_json(path, entries)


def all_item_ids():
    ids = []
    for name in ("buildings.json", "units.json", "specials.json"):
        ids.extend(
            entry["legacy_id"]
            for entry in load_json(NORMALIZED / name))
    return ids


def other_union_id(exclude):
    for legacy_id in all_item_ids():
        if legacy_id not in exclude:
            return legacy_id
    raise AssertionError("no alternate union id available")


def failure_problems(test, repo_root):
    code, out, err = run_main(repo_root)
    test.assertEqual(code, 1, "expected exit 1, got %d (stderr=%r)"
                     % (code, err))
    payload = json.loads(out)
    test.assertEqual(payload.get("result"), "validation-failed")
    return payload["problems"]


def assert_problem(test, problems, family, file=None, field=None,
                   message_part=None):
    for item in problems:
        if item["family"] != family:
            continue
        if file is not None and item["file"] != file:
            continue
        if field is not None and item["field"] != field:
            continue
        if message_part is not None and message_part not in item["message"]:
            continue
        return item
    test.fail("no problem matching family=%r file=%r field=%r "
              "message_part=%r in %r"
              % (family, file, field, message_part, problems))


class TestStructureManifest(unittest.TestCase):
    def test_committed_package_is_valid(self):
        code, out, err = run_main(ROOT)
        self.assertEqual(code, 0, "stderr=%r stdout=%r" % (err, out))
        report = json.loads(out)
        self.assertEqual(report["result"], "valid")
        self.assertEqual(report["files_verified"], 22)
        self.assertEqual(report["schemas_verified"], 21)
        self.assertEqual(report["counts_checked"], 22)
        self.assertIsInstance(report["references_checked"], int)
        self.assertGreater(report["references_checked"], 0)

    def test_success_report_entries_match_files(self):
        code, out, _err = run_main(ROOT)
        self.assertEqual(code, 0)
        report = json.loads(out)
        for name in sorted(validator.FILE_MAP):
            actual = len(load_json(NORMALIZED / name))
            self.assertEqual(report["entries"][name], actual, name)

    def test_mapping_covers_package_exactly(self):
        on_disk = sorted(path.name for path in NORMALIZED.iterdir()
                         if path.is_file())
        self.assertEqual(sorted(validator.FILE_MAP), on_disk)
        schema_names = sorted(
            spec[2] for spec in validator.FILE_MAP.values()
            if spec[2] is not None)
        self.assertEqual(len(schema_names), 21)
        self.assertEqual(
            schema_names,
            sorted(path.name for path in SCHEMAS.iterdir()))

    def test_unrecorded_file_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)
            normalized_path(repo, "zzz_extra.json").write_text(
                "[]", encoding="utf-8")
            problems = failure_problems(self, repo)
            item = assert_problem(
                self, problems, validator.FAMILY_STRUCTURE,
                file="zzz_extra.json")
            self.assertIn("unrecorded", item["message"])

    def test_missing_recorded_output_is_invalid_input(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)
            normalized_path(repo, "units.json").unlink()
            code, out, err = run_main(repo)
            self.assertEqual(code, 2)
            self.assertEqual(out, "")
            self.assertIn("units.json", err)

    def test_unparseable_output_is_invalid_input(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)
            normalized_path(repo, "quests.json").write_text(
                "{", encoding="utf-8")
            code, out, err = run_main(repo)
            self.assertEqual(code, 2)
            self.assertEqual(out, "")
            self.assertIn("quests.json", err)

    def test_tampered_bytes_fail_digest(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)
            path = normalized_path(repo, "quests.json")
            path.write_bytes(path.read_bytes() + b" ")
            problems = failure_problems(self, repo)
            assert_problem(
                self, problems, validator.FAMILY_MANIFEST,
                file="quests.json", field="sha256")

    def test_count_drift_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)
            manifest_path = Path(repo) / "packages/game-content/manifest.json"
            manifest = load_json(manifest_path)
            manifest["quests"]["counts"]["quests"] = 90
            save_json(manifest_path, manifest)
            problems = failure_problems(self, repo)
            assert_problem(
                self, problems, validator.FAMILY_MANIFEST,
                file="quests.json", field="quests")

    def test_missing_section_record_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)
            manifest_path = Path(repo) / "packages/game-content/manifest.json"
            manifest = load_json(manifest_path)
            del manifest["darts"]
            save_json(manifest_path, manifest)
            problems = failure_problems(self, repo)
            assert_problem(
                self, problems, validator.FAMILY_STRUCTURE,
                field="darts", message_part="extension section record")

    def test_invalid_schema_is_invalid_input(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)
            schema = (Path(repo) / "packages/game-content/schemas/"
                      "quest.schema.json")
            schema.write_text("{}", encoding="utf-8")
            code, out, err = run_main(repo)
            self.assertEqual(code, 2)
            self.assertEqual(out, "")
            self.assertIn("quest.schema.json", err)

    def test_missing_schema_is_invalid_input(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)
            schema = (Path(repo) / "packages/game-content/schemas/"
                      "sound.schema.json")
            schema.unlink()
            code, out, err = run_main(repo)
            self.assertEqual(code, 2)
            self.assertEqual(out, "")
            self.assertIn("sound.schema.json", err)

    def test_output_outside_package_is_invalid_input(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)
            manifest_path = Path(repo) / "packages/game-content/manifest.json"
            manifest = load_json(manifest_path)
            manifest["quests"]["outputs"][0]["file"] = "elsewhere/x.json"
            save_json(manifest_path, manifest)
            code, out, err = run_main(repo)
            self.assertEqual(code, 2)
            self.assertEqual(out, "")
            self.assertIn("outside the package", err)

    def test_unknown_argument_is_invalid_usage(self):
        code, out, err = run_main(ROOT, argv=["--nope"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("unknown argument", err)

    def test_help_prints_usage(self):
        code, out, _err = run_main(ROOT, argv=["--help"])
        self.assertEqual(code, 0)
        self.assertIn("usage", out)


class TestSchemaConformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schemas = {}
        for name, (_section, _count, schema_name) in \
                sorted(validator.FILE_MAP.items()):
            if schema_name is None:
                continue
            cls.schemas[name] = load_json(SCHEMAS / schema_name)

    def entries(self, name):
        return load_json(NORMALIZED / name)

    def test_every_committed_entry_passes_its_schema(self):
        for name, schema in sorted(self.schemas.items()):
            for entry in self.entries(name):
                self.assertEqual(
                    validator.check_entry(entry, schema), [],
                    "%s entry %r" % (name, entry.get("legacy_id")))

    def test_required_field_traceability(self):
        for name, schema in sorted(self.schemas.items()):
            entry = copy.deepcopy(self.entries(name)[0])
            for field in schema["required"]:
                mutated = copy.deepcopy(entry)
                del mutated[field]
                problems = validator.check_entry(mutated, schema)
                self.assertTrue(
                    any(f == field and "missing required" in message
                        for f, message in problems),
                    "%s must catch missing %s, got %r"
                    % (name, field, problems))

    def find_property(self, predicate):
        for name, schema in sorted(self.schemas.items()):
            entry = self.entries(name)[0]
            for field, spec in schema["properties"].items():
                if not isinstance(spec, dict) or not predicate(spec):
                    continue
                if field not in entry:
                    continue
                return name, field, spec
        raise AssertionError("no schema property matched the predicate")

    def test_type_violation_caught(self):
        name, field, spec = self.find_property(
            lambda s: s.get("type") == "integer" and "const" not in s)
        entry = self.entries(name)[0]
        self.assertIn(field, entry)
        mutated = copy.deepcopy(entry)
        mutated[field] = "not-a-number"
        problems = validator.check_entry(mutated, self.schemas[name])
        self.assertIn((field, "type mismatch: expected integer"), problems)

    def test_const_violation_caught(self):
        name = "buildings.json"
        schema = self.schemas[name]
        mutated = copy.deepcopy(self.entries(name)[0])
        mutated["kind"] = "wrong"
        problems = validator.check_entry(mutated, schema)
        self.assertIn(("kind", "const mismatch"), problems)

    def test_enum_violation_caught(self):
        name, field, spec = self.find_property(
            lambda s: "enum" in s and s.get("type") == "string")
        mutated = copy.deepcopy(self.entries(name)[0])
        self.assertIsInstance(mutated[field], str)
        mutated[field] = "__not_in_enum__"
        problems = validator.check_entry(mutated, self.schemas[name])
        self.assertIn((field, "enum mismatch"), problems)

    def test_property_level_minimum_caught(self):
        name, field, spec = self.find_property(
            lambda s: "minimum" in s and s.get("type") == "integer")
        mutated = copy.deepcopy(self.entries(name)[0])
        mutated[field] = spec["minimum"] - 1
        problems = validator.check_entry(mutated, self.schemas[name])
        self.assertIn((field, "value below minimum"), problems)

    def test_array_element_type_caught(self):
        name = "collections.json"
        schema = self.schemas[name]
        mutated = copy.deepcopy(self.entries(name)[0])
        mutated["item_refs"][0] = 12
        problems = validator.check_entry(mutated, schema)
        self.assertTrue(
            any(f == "item_refs[0]" and "type mismatch" in message
                for f, message in problems),
            problems)

    def test_min_items_caught(self):
        name = "magics.json"
        schema = self.schemas[name]
        mutated = copy.deepcopy(self.entries(name)[0])
        mutated["area"] = []
        problems = validator.check_entry(mutated, schema)
        self.assertIn(("area", "array below minItems"), problems)

    def test_min_properties_caught(self):
        name = "collections.json"
        schema = self.schemas[name]
        mutated = copy.deepcopy(self.entries(name)[0])
        mutated["prize"] = {}
        problems = validator.check_entry(mutated, schema)
        self.assertIn(("prize", "object below minProperties"), problems)

    def test_nested_value_type_and_minimum_caught(self):
        name = "collections.json"
        schema = self.schemas[name]
        spec = schema["properties"]["prize"]
        nested = spec["additionalProperties"]
        key = next(iter(self.entries(name)[0]["prize"]))
        mutated = copy.deepcopy(self.entries(name)[0])
        mutated["prize"][key] = "not-a-number"
        problems = validator.check_entry(mutated, schema)
        self.assertTrue(
            any(f == "prize." + key and "type mismatch" in message
                for f, message in problems), problems)
        mutated["prize"][key] = nested["minimum"] - 1
        problems = validator.check_entry(mutated, schema)
        self.assertIn(
            ("prize." + key, "value below minimum"), problems)

    def test_property_names_caught(self):
        name = "buildings.json"
        schema = self.schemas[name]
        self.assertIn(
            "propertyNames", schema["properties"]["costs"])
        mutated = copy.deepcopy(self.entries(name)[0])
        mutated["costs"]["__bogus__"] = 1
        problems = validator.check_entry(mutated, schema)
        self.assertTrue(
            any(f == "costs" and "property name outside set" in message
                for f, message in problems), problems)

    def test_additional_property_caught(self):
        name = "quests.json"
        schema = self.schemas[name]
        self.assertIs(schema.get("additionalProperties"), False)
        mutated = copy.deepcopy(self.entries(name)[0])
        mutated["__extra__"] = 1
        problems = validator.check_entry(mutated, schema)
        self.assertIn(
            ("__extra__", "additional property not in schema"), problems)

    def test_special_requires_exactly_one_entry(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)

            def change(entries):
                entries.append(copy.deepcopy(entries[0]))
            mutate(repo, "specials.json", change)
            problems = failure_problems(self, repo)
            assert_problem(
                self, problems, validator.FAMILY_SPECIAL,
                file="specials.json", message_part="exactly one")

    def test_special_id_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)
            mutate(repo, "specials.json",
                   lambda entries: entries[0].__setitem__(
                       "legacy_id", "926"))
            problems = failure_problems(self, repo)
            assert_problem(
                self, problems, validator.FAMILY_SPECIAL,
                file="specials.json", field="legacy_id")

    def test_special_note_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)
            mutate(repo, "specials.json",
                   lambda entries: entries[0].__setitem__(
                       "special_note", "altered"))
            problems = failure_problems(self, repo)
            assert_problem(
                self, problems, validator.FAMILY_SPECIAL,
                file="specials.json", field="special_note")

    def test_special_kind_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)
            mutate(repo, "specials.json",
                   lambda entries: entries[0].__setitem__(
                       "kind", "building"))
            problems = failure_problems(self, repo)
            assert_problem(
                self, problems, validator.FAMILY_SPECIAL,
                file="specials.json", field="kind")


class TestDependencies(unittest.TestCase):
    def test_duplicate_legacy_id_in_file(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)

            def change(entries):
                entries.append(copy.deepcopy(entries[0]))
            mutate(repo, "levels.json", change)
            problems = failure_problems(self, repo)
            assert_problem(
                self, problems, validator.FAMILY_DEPENDENCY,
                file="levels.json", field="legacy_id",
                message_part="duplicate legacy_id")

    def test_cross_file_duplicate_breaks_union(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)
            buildings = load_json(NORMALIZED / "buildings.json")
            shared = buildings[0]["legacy_id"]

            def change(entries):
                entries[0]["legacy_id"] = shared
            mutate(repo, "units.json", change)
            problems = failure_problems(self, repo)
            assert_problem(
                self, problems, validator.FAMILY_DEPENDENCY,
                file="items-union", field="legacy_id")

    def test_relation_unresolvable(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)
            mutate(repo, "buildings.json",
                   lambda entries: entries[0].__setitem__(
                       "upgrades_to", 99999999))
            problems = failure_problems(self, repo)
            assert_problem(
                self, problems, validator.FAMILY_DEPENDENCY,
                file="buildings.json", field="upgrades_to",
                message_part="unresolvable")

    def test_relation_sentinels_allowed(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)

            def change(entries):
                entries[0]["upgrades_to"] = 0
                entries[0]["trains_ids"] = -1
            mutate(repo, "buildings.json", change)
            problems = failure_problems(self, repo)
            self.assertFalse(
                any(item["field"] in ("upgrades_to", "trains_ids")
                    for item in problems),
                problems)

    def test_inventory_key_unresolvable(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)
            target = None
            for name in ("buildings.json", "units.json", "specials.json"):
                for index, entry in enumerate(load_json(NORMALIZED / name)):
                    if isinstance(entry.get("inventory_ids"), dict):
                        target = (name, index)
                        break
                if target:
                    break
        self.assertIsNotNone(target, "no items entry carries inventory_ids")
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)
            name, index = target

            def change(entries):
                entries[index]["inventory_ids"]["99999999"] = 1
            mutate(repo, name, change)
            problems = failure_problems(self, repo)
            assert_problem(
                self, problems, validator.FAMILY_DEPENDENCY,
                file=name, field="inventory_ids",
                message_part="unresolvable inventory_ids key")

    def test_collection_refs_drift_caught(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)

            def change(entries):
                refs = entries[0]["item_refs"]
                refs[0] = refs[1]
            mutate(repo, "collections.json", change)
            problems = failure_problems(self, repo)
            assert_problem(
                self, problems, validator.FAMILY_DEPENDENCY,
                file="collections.json", field="item_refs",
                message_part="derived")

    def test_collection_refs_unresolvable(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)

            def change(entries):
                entries[0]["item_refs"][0] = "999999999"
            mutate(repo, "collections.json", change)
            problems = failure_problems(self, repo)
            assert_problem(
                self, problems, validator.FAMILY_DEPENDENCY,
                file="collections.json", field="item_refs",
                message_part="unresolvable reference")

    def test_prize_refs_drift_caught(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)
            substitute = other_union_id(set())

            def change(entries):
                entries[0]["prize_refs"][0] = substitute
            mutate(repo, "collections.json", change)
            problems = failure_problems(self, repo)
            assert_problem(
                self, problems, validator.FAMILY_DEPENDENCY,
                file="collections.json", field="prize_refs",
                message_part="derived")

    def test_ranking_refs_drift_caught(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)
            substitute = other_union_id(set())

            def change(entries):
                entries[0]["unit_refs"][0] = substitute
            mutate(repo, "level_ranking_reward.json", change)
            problems = failure_problems(self, repo)
            assert_problem(
                self, problems, validator.FAMILY_DEPENDENCY,
                file="level_ranking_reward.json", field="unit_refs",
                message_part="derived")

    def test_ranking_refs_unresolvable(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)

            def change(entries):
                entries[0]["unit_refs"][0] = "999999999"
            mutate(repo, "level_ranking_reward.json", change)
            problems = failure_problems(self, repo)
            assert_problem(
                self, problems, validator.FAMILY_DEPENDENCY,
                file="level_ranking_reward.json", field="unit_refs",
                message_part="unresolvable reference")

    def test_unit_collection_refs_drift_and_resolution(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)
            substitute = other_union_id(set())

            def change(entries):
                entries[0]["unit_refs"][0] = substitute
            mutate(repo, "unit_collection_categories.json", change)
            problems = failure_problems(self, repo)
            assert_problem(
                self, problems, validator.FAMILY_DEPENDENCY,
                file="unit_collection_categories.json", field="unit_refs",
                message_part="derived")

    def test_darts_refs_drift_and_extra_ref(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)
            substitute = other_union_id(set())

            def change(entries):
                entries[0]["item_refs"][0] = substitute
                entries[0]["extra_ref"] = substitute
            mutate(repo, "darts_items.json", change)
            problems = failure_problems(self, repo)
            assert_problem(
                self, problems, validator.FAMILY_DEPENDENCY,
                file="darts_items.json", field="item_refs",
                message_part="derived")
            assert_problem(
                self, problems, validator.FAMILY_DEPENDENCY,
                file="darts_items.json", field="extra_ref",
                message_part="derived")

    def test_offer_refs_drift_caught(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)
            substitute = other_union_id(set())

            def change(entries):
                for entry in entries:
                    if entry["item_refs"]:
                        entry["item_refs"][0] = substitute
                        return
                raise AssertionError("no offer carries item_refs")
            mutate(repo, "offer_packs.json", change)
            problems = failure_problems(self, repo)
            assert_problem(
                self, problems, validator.FAMILY_DEPENDENCY,
                file="offer_packs.json", field="item_refs",
                message_part="derived")

    def test_offer_unresolvable_leaf_caught(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)

            def change(entries):
                for entry in entries:
                    if entry["items_shape"] == "flat":
                        entry["items"].append(999999999)
                        return
                raise AssertionError("no flat offer available")
            mutate(repo, "offer_packs.json", change)
            problems = failure_problems(self, repo)
            assert_problem(
                self, problems, validator.FAMILY_DEPENDENCY,
                file="offer_packs.json", field="item_refs",
                message_part="unresolvable offer leaf")

    def test_offer_pair_second_anomaly_pinned(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)

            def change(entries):
                for entry in entries:
                    if entry["id"] == validator.ANOMALY_OFFER_ID:
                        entry["items"][0][1] = 36
                        return
                raise AssertionError("pinned pair offer missing")
            mutate(repo, "offer_packs.json", change)
            problems = failure_problems(self, repo)
            assert_problem(
                self, problems, validator.FAMILY_DEPENDENCY,
                file="offer_packs.json", field="items",
                message_part="pinned anomaly")

    def test_offer_float_anomaly_pinned(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)

            def change(entries):
                for entry in entries:
                    if entry["id"] != validator.ANOMALY_FLOAT_OFFER_ID:
                        continue
                    for group in entry["items"]:
                        if not isinstance(group, list):
                            continue
                        for index, value in enumerate(group):
                            if value == validator.ANOMALY_FLOAT_VALUE:
                                group[index] = 1072.1225
                                return
                raise AssertionError("pinned float anomaly missing")
            mutate(repo, "offer_packs.json", change)
            problems = failure_problems(self, repo)
            assert_problem(
                self, problems, validator.FAMILY_DEPENDENCY,
                file="offer_packs.json", field="items",
                message_part="pinned anomaly")

    def test_categories_parent_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)

            def change(entries):
                entries[0]["sub"][0]["parent"] = 99
            mutate(repo, "categories.json", change)
            problems = failure_problems(self, repo)
            assert_problem(
                self, problems, validator.FAMILY_DEPENDENCY,
                file="categories.json", message_part="does not equal")

    def test_categories_parent_not_integer(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)

            def change(entries):
                entries[0]["sub"][0]["parent"] = "1"
            mutate(repo, "categories.json", change)
            problems = failure_problems(self, repo)
            assert_problem(
                self, problems, validator.FAMILY_DEPENDENCY,
                file="categories.json", message_part="not native integer")


class TestCliContainment(unittest.TestCase):
    def test_report_is_deterministic(self):
        first_code, first_out, _err = run_cli(ROOT)
        second_code, second_out, _err = run_cli(ROOT)
        self.assertEqual(first_code, 0)
        self.assertEqual(second_code, 0)
        self.assertEqual(first_out, second_out)

    def test_subprocess_exit_codes(self):
        code, out, _err = run_cli(ROOT)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["result"], "valid")

        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)
            mutate(repo, "quests.json",
                   lambda entries: entries[0].pop("title"))
            code, out, _err = run_cli(repo)
            self.assertEqual(code, 1)
            payload = json.loads(out)
            self.assertEqual(payload["result"], "validation-failed")
            assert_problem(
                self, payload["problems"], validator.FAMILY_SCHEMA,
                file="quests.json", field="title")

        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)
            normalized_path(repo, "sounds.json").unlink()
            code, out, err = run_cli(repo)
            self.assertEqual(code, 2)
            self.assertEqual(out, b"")
            self.assertIn(b"sounds.json", err)

    def test_committed_package_unchanged_by_run(self):
        before = snapshot(PACKAGE)
        code, _out, _err = run_main(ROOT)
        self.assertEqual(code, 0)
        self.assertEqual(snapshot(PACKAGE), before)

    def test_failed_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = copy_repo(temp)
            package = Path(repo) / "packages/game-content"
            mutate(repo, "quests.json",
                   lambda entries: entries[0].pop("title"))
            before = snapshot(package)
            code, _out, _err = run_main(repo)
            self.assertEqual(code, 1)
            self.assertEqual(snapshot(package), before)

    def test_source_carries_no_forbidden_tokens(self):
        source = TOOL.read_text(encoding="utf-8").lower()
        for token in FORBIDDEN_SOURCE_TOKENS:
            self.assertNotIn(
                token.lower(), source,
                "validator source must not reference %r" % token)


if __name__ == "__main__":
    unittest.main()
