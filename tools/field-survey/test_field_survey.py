import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

import verify_fields as verifier

ROOT = Path(__file__).resolve().parents[2]

EXPECTED_ARRAY_KEYS = [
    "items", "expansion_prices", "levels", "neighbor_assists",
    "town_prices", "map_prices", "findable_items", "goals",
    "offer_packs", "social_items", "sounds", "collections",
    "level_ranking_reward", "darts_items", "magics",
]

EXPECTED_OBJECT_KEYS = [
    "categories", "inventory_items", "globals", "images",
    "units_collections_categories",
]

# Trailing newlines keep every survey source reference (max end_line 51254)
# in range so crafted-shape failures surface deterministically.
SHAPE_PADDING = "\n" * 51260

EXPECTED_READS = frozenset([
    "config/main.json",
    "docs/game-content/field-types.json",
    "docs/game-content/field-types.md",
])


def snapshot(root):
    return {str(path.relative_to(root)): ("directory" if path.is_dir() else
            path.read_bytes())
            for path in Path(root).rglob("*")}


def run_main(argv):
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        code = verifier.main(argv)
    return code, stderr.getvalue()


def run_stdout(argv):
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        code, _ = run_main(argv)
    return code, stdout.getvalue()


def make_work_tree():
    temporary = tempfile.TemporaryDirectory()
    work = Path(temporary.name) / "repo"
    shutil.copytree(ROOT / "config", work / "config")
    shutil.copytree(ROOT / "docs" / "game-content", work / "docs" / "game-content")
    (work / "tools" / "field-survey").mkdir(parents=True)
    shutil.copy2(ROOT / "tools" / "field-survey" / "verify_fields.py",
                 work / "tools" / "field-survey" / "verify_fields.py")
    return temporary, work


class PredicateTests(unittest.TestCase):
    def test_numeric_grammar_accepts_plain_and_signed_values(self):
        for text in ("0", "-0", "+0", "42", "-17", "+8", "007", "1046",
                     "3.14", "-0.5", "+2.0", "0.0", ".7", "+.5", "-.5",
                     "1e3", "1E3", "1e+3", "1e-3", "-2.5E-2", "+1.5e+10"):
            self.assertTrue(verifier.is_string_encoded_number(text),
                            "should be numeric: %r" % (text,))

    def test_numeric_grammar_rejects_whitespace_hex_separators_and_words(self):
        for text in ("", " ", " 12", "12 ", " 12 ", "12\n", "\t12",
                     "0x10", "0XFF", "0b10", "1,000", "1_000",
                     "Infinity", "-Infinity", "+Infinity", "NaN",
                     "null", "true", "1.2.3", ".", "+", "-", "e10",
                     "1e", "1e+", "--1", "++1", "+-1", "5.", ".e3",
                     "12.121.0", "2012-01-31", "1046.1, 1055.1", "1,1",
                     "Oil QA Supervisor"):
            self.assertFalse(verifier.is_string_encoded_number(text),
                             "should not be numeric: %r" % (text,))

    def test_numeric_grammar_rejects_non_strings(self):
        for value in (12, 3.5, None, True, [], {}):
            self.assertFalse(verifier.is_string_encoded_number(value))

    def test_embedded_json_accepts_any_decoder_success(self):
        for text in ("0", "-1.5", "1e3", "null", "true", "false",
                     "123", '"hi"', '""', "[]", "[1,2]", "[66,67]",
                     "{}", '{"a":1}', " 12", "12 ", "  [1]  ",
                     "Infinity", "-Infinity", "NaN", "null "):
            self.assertTrue(verifier.is_embedded_json_string(text),
                            "should be embedded json: %r" % (text,))

    def test_embedded_json_rejects_unparseable_and_empty(self):
        for text in ("", "abc", "0x10", "1,000", ".7", "5.",
                     "12.121.0", "{broken", "[1,", '{"a":',
                     "2012-01-31 23:00:00", "Oil QA Supervisor",
                     "   ", "12.121.0,12.121.0", "'single'", "undefined"):
            self.assertFalse(verifier.is_embedded_json_string(text),
                             "should not be embedded json: %r" % (text,))

    def test_embedded_json_rejects_non_strings(self):
        for value in (12, 3.5, None, True, [], {}):
            self.assertFalse(verifier.is_embedded_json_string(value))

    def test_predicates_are_independent(self):
        # Whitespace-padded JSON is embedded but never numeric; the string
        # null is embedded JSON but never a number; a leading-dot fraction
        # is numeric per the grammar but the decoder rejects it.
        self.assertTrue(verifier.is_embedded_json_string(" 12"))
        self.assertFalse(verifier.is_string_encoded_number(" 12"))
        self.assertTrue(verifier.is_embedded_json_string("null"))
        self.assertFalse(verifier.is_string_encoded_number("null"))
        self.assertTrue(verifier.is_embedded_json_string("Infinity"))
        self.assertFalse(verifier.is_string_encoded_number("Infinity"))
        self.assertTrue(verifier.is_string_encoded_number(".7"))
        self.assertFalse(verifier.is_embedded_json_string(".7"))
        # A leading plus is numeric per the grammar but the JSON decoder
        # rejects it, so it is never embedded JSON.
        self.assertTrue(verifier.is_string_encoded_number("+2"))
        self.assertFalse(verifier.is_embedded_json_string("+2"))

    def test_booleans_classify_before_numbers(self):
        self.assertEqual(verifier.classify_json_value(True), "boolean")
        self.assertEqual(verifier.classify_json_value(False), "boolean")


class ExtractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = verifier.load_main_config(ROOT / "config" / "main.json")
        cls.arrays, cls.objects, cls.whole = verifier.extract_survey(config)

    def test_key_partition_matches_canonical_order(self):
        config = verifier.load_main_config(ROOT / "config" / "main.json")
        self.assertEqual([key for key in config if key in self.arrays],
                         EXPECTED_ARRAY_KEYS)
        self.assertEqual([key for key in config if key in self.objects],
                         EXPECTED_OBJECT_KEYS)

    def test_whole_file_counts_match_reference(self):
        self.assertEqual(self.whole,
                         {"string_count": 43544, "number_count": 2997,
                          "boolean_count": 0, "null_count": 780})

    def test_items_id_is_fully_string_encoded(self):
        profile = self.arrays["items"]["fields"]["id"]
        self.assertEqual(profile["presence_count"], 778)
        self.assertEqual(profile["types"]["string"], 778)
        self.assertEqual(profile["string_encoded_number_count"], 778)
        self.assertEqual(profile["embedded_json_string_count"], 778)
        self.assertEqual(profile["empty_string_count"], 0)
        self.assertEqual(profile["null_count"], 0)

    def test_items_cost_type_is_always_null(self):
        profile = self.arrays["items"]["fields"]["cost_type"]
        self.assertEqual(profile["presence_count"], 778)
        self.assertEqual(profile["types"]["null"], 778)
        self.assertEqual(profile["null_count"], 778)

    def test_items_best_against_mixed_content(self):
        profile = self.arrays["items"]["fields"]["best_against"]
        self.assertEqual(profile["presence_count"], 778)
        self.assertEqual(profile["empty_string_count"], 299)
        self.assertEqual(profile["string_encoded_number_count"], 138)

    def test_items_field_count(self):
        self.assertEqual(len(self.arrays["items"]["fields"]), 53)

    def test_goals_hint_all_empty_and_id_native(self):
        hint = self.arrays["goals"]["fields"]["hint"]
        self.assertEqual(hint["empty_string_count"], 91)
        identifier = self.arrays["goals"]["fields"]["id"]
        self.assertEqual(identifier["types"]["number"], 91)
        self.assertEqual(identifier["types"]["string"], 0)

    def test_levels_fields_are_homogeneous(self):
        required = self.arrays["levels"]["fields"]["exp_required"]
        self.assertEqual(required["types"]["number"], 100)
        name = self.arrays["levels"]["fields"]["name"]
        self.assertEqual(name["types"]["string"], 100)
        self.assertEqual(name["string_encoded_number_count"], 0)

    def test_magics_area_is_embedded_json(self):
        area = self.arrays["magics"]["fields"]["area"]
        self.assertEqual(area["types"]["string"], 10)
        self.assertEqual(area["embedded_json_string_count"], 10)
        self.assertEqual(area["string_encoded_number_count"], 0)

    def test_sounds_fully_string_encoded(self):
        for name in ("id", "loops", "max", "preload"):
            profile = self.arrays["sounds"]["fields"][name]
            self.assertEqual(profile["types"]["string"], 139)
            self.assertEqual(profile["string_encoded_number_count"], 139)

    def test_offer_packs_items_mixed_null_and_array(self):
        profile = self.arrays["offer_packs"]["fields"]["items"]
        self.assertEqual(profile["types"]["array"], 43)
        self.assertEqual(profile["types"]["null"], 1)
        self.assertEqual(profile["null_count"], 1)

    def test_darts_start_date_is_plain_string(self):
        profile = self.arrays["darts_items"]["fields"]["start_date"]
        self.assertEqual(profile["types"]["string"], 30)
        self.assertEqual(profile["string_encoded_number_count"], 0)
        self.assertEqual(profile["embedded_json_string_count"], 0)

    def test_globals_value_shape(self):
        self.assertEqual(self.objects["globals"]["value_types"],
                         {"string": 8, "number": 66, "boolean": 0,
                          "null": 0, "array": 22, "object": 8})

    def test_images_all_locale_strings(self):
        self.assertEqual(self.objects["images"]["value_types"],
                         {"string": 607, "number": 0, "boolean": 0,
                          "null": 0, "array": 0, "object": 0})

    def test_non_object_array_entry_is_unsupported(self):
        with self.assertRaisesRegex(verifier.VerificationError,
                                    "array entry is not an object"):
            verifier.profile_array_key([{"id": 1}, "oops"])

    def test_top_level_list_is_unsupported(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "main.json"
            candidate.write_text("[1, 2, 3]", encoding="utf-8")
            with self.assertRaisesRegex(verifier.VerificationError,
                                        "unsupported content shape"):
                verifier.load_main_config(candidate)

    def test_non_container_key_is_unsupported(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "main.json"
            candidate.write_text('{"items": 42}', encoding="utf-8")
            with self.assertRaisesRegex(verifier.VerificationError,
                                        "unsupported content shape"):
                verifier.load_main_config(candidate)


class VerificationExitCodeTests(unittest.TestCase):
    def setUp(self):
        self.temporary, self.work = make_work_tree()
        self.addCleanup(self.temporary.cleanup)

    def load_survey(self):
        return json.loads(
            (self.work / "docs" / "game-content" / "field-types.json").read_text(
                encoding="utf-8"))

    def save_survey(self, document):
        (self.work / "docs" / "game-content" / "field-types.json").write_text(
            json.dumps(document, indent=2) + "\n", encoding="utf-8")

    def test_agreement_exit_0(self):
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 0)

    def test_whole_file_drift_exit_1(self):
        document = self.load_survey()
        document["whole_file"]["string_count"] += 1
        self.save_survey(document)
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 1)

    def test_field_type_drift_exit_1(self):
        document = self.load_survey()
        for entry in document["array_keys"]:
            if entry["name"] == "goals":
                field = entry["fields"]["id"]
                field["types"]["number"] -= 1
                field["types"]["string"] += 1
        self.save_survey(document)
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 1)

    def test_field_metric_drift_exit_1(self):
        document = self.load_survey()
        for entry in document["array_keys"]:
            if entry["name"] == "items":
                entry["fields"]["id"]["string_encoded_number_count"] = 777
        self.save_survey(document)
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 1)

    def test_missing_field_exit_1(self):
        document = self.load_survey()
        for entry in document["array_keys"]:
            if entry["name"] == "magics":
                del entry["fields"]["area"]
        self.save_survey(document)
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 1)

    def test_entry_count_drift_exit_1(self):
        document = self.load_survey()
        for entry in document["array_keys"]:
            if entry["name"] == "levels":
                entry["entry_count"] = 101
        self.save_survey(document)
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 1)

    def test_object_value_shape_drift_exit_1(self):
        document = self.load_survey()
        for entry in document["object_keys"]:
            if entry["name"] == "globals":
                entry["value_types"]["number"] -= 1
                entry["value_types"]["string"] += 1
        self.save_survey(document)
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 1)

    def test_readable_drift_exit_1(self):
        readable = self.work / "docs" / "game-content" / "field-types.md"
        text = readable.read_text(encoding="utf-8")
        readable.write_text(text.replace("| `magics` | mixed |",
                                         "| `gone_key` | mixed |"),
                            encoding="utf-8")
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 1)

    def test_unsupported_top_level_exit_2(self):
        (self.work / "config" / "main.json").write_text(
            "[1, 2, 3]" + SHAPE_PADDING, encoding="utf-8")
        code, stderr = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 2)
        self.assertIn("unsupported content shape", stderr)

    def test_unsupported_key_shape_exit_2(self):
        (self.work / "config" / "main.json").write_text(
            '{"items": 42}' + SHAPE_PADDING, encoding="utf-8")
        code, stderr = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 2)
        self.assertIn("unsupported content shape", stderr)

    def test_unsupported_array_entry_exit_2(self):
        (self.work / "config" / "main.json").write_text(
            '{"items": ["oops"]}' + SHAPE_PADDING, encoding="utf-8")
        code, stderr = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 2)
        self.assertIn("array entry is not an object", stderr)

    def test_invalid_survey_exit_2(self):
        (self.work / "docs" / "game-content" / "field-types.json").write_text(
            "{broken", encoding="utf-8")
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 2)

    def test_grammar_tamper_exit_2(self):
        document = self.load_survey()
        document["predicates"]["string_encoded_number"]["grammar"] += "x"
        self.save_survey(document)
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 2)

    def test_unparseable_content_exit_2(self):
        (self.work / "config" / "main.json").write_text("{broken",
                                                        encoding="utf-8")
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 2)

    def test_missing_readable_exit_2(self):
        (self.work / "docs" / "game-content" / "field-types.md").unlink()
        code, _ = run_main(["--repo-root", str(self.work)])
        self.assertEqual(code, 2)


class ConsistencyAndContainmentTests(unittest.TestCase):
    def test_survey_matches_source_profiles(self):
        config = verifier.load_main_config(ROOT / "config" / "main.json")
        arrays, objects, whole = verifier.extract_survey(config)
        survey = json.loads((ROOT / "docs" / "game-content" / "field-types.json").read_text(
            encoding="utf-8"))
        self.assertEqual(survey["policy"]["key_count"], 20)
        self.assertEqual(survey["policy"]["array_key_count"], 15)
        self.assertEqual(survey["policy"]["object_key_count"], 5)
        self.assertEqual(survey["whole_file"], whole)
        self.assertEqual(survey["predicates"]["string_encoded_number"]["grammar"],
                         verifier.NUMERIC_GRAMMAR)
        survey_arrays = {entry["name"]: entry for entry in survey["array_keys"]}
        self.assertEqual(sorted(survey_arrays), sorted(EXPECTED_ARRAY_KEYS))
        for name, source in arrays.items():
            self.assertEqual(survey_arrays[name]["entry_count"],
                             source["entry_count"])
            self.assertEqual(survey_arrays[name]["fields"], source["fields"])
        survey_objects = {entry["name"]: entry for entry in survey["object_keys"]}
        self.assertEqual(sorted(survey_objects), sorted(EXPECTED_OBJECT_KEYS))
        for name, source in objects.items():
            self.assertEqual(survey_objects[name]["entry_count"],
                             source["entry_count"])
            self.assertEqual(survey_objects[name]["value_types"],
                             source["value_types"])

    def test_readable_covers_every_survey_entry(self):
        survey = json.loads((ROOT / "docs" / "game-content" / "field-types.json").read_text(
            encoding="utf-8"))
        readable = (ROOT / "docs" / "game-content" / "field-types.md").read_text(
            encoding="utf-8")
        for entry in survey["array_keys"]:
            self.assertIn("| `" + entry["name"] + "` | "
                          + entry["encoding_class"] + " |", readable)
        for entry in survey["object_keys"]:
            self.assertIn("| `" + entry["name"] + "` | object |", readable)
        self.assertIn("Observed encodings", readable)
        self.assertIn("Normalization", readable)
        self.assertIn("mixed", readable)
        self.assertIn(verifier.NUMERIC_GRAMMAR, readable)

    def test_mixed_keys_labeled_explicitly(self):
        survey = json.loads((ROOT / "docs" / "game-content" / "field-types.json").read_text(
            encoding="utf-8"))
        mixed = sorted(entry["name"] for entry in survey["array_keys"]
                       if entry["encoding_class"] == "mixed")
        self.assertEqual(mixed, ["darts_items", "findable_items", "goals",
                                 "level_ranking_reward", "levels", "magics",
                                 "neighbor_assists", "offer_packs",
                                 "social_items"])
        readable = (ROOT / "docs" / "game-content" / "field-types.md").read_text(
            encoding="utf-8")
        for name in mixed:
            self.assertIn("| `" + name + "` | mixed |", readable)

    def test_repeated_runs_are_byte_identical(self):
        code_one, out_one = run_stdout(["--repo-root", str(ROOT)])
        code_two, out_two = run_stdout(["--repo-root", str(ROOT)])
        self.assertEqual(code_one, 0)
        self.assertEqual(code_two, 0)
        self.assertEqual(out_one, out_two)

    def test_verifier_reads_only_expected_files_and_writes_nothing(self):
        temporary, work = make_work_tree()
        try:
            opened = []
            real_io_open = io.open

            def guarded_open(file, mode="r", *args, **kwargs):
                if any(flag in str(mode) for flag in ("w", "a", "x", "+")):
                    raise AssertionError("unexpected write open: %r" % (file,))
                opened.append(str(file))
                return real_io_open(file, mode, *args, **kwargs)

            before = snapshot(work)
            # pathlib.Path.read_bytes resolves to io.open, not builtins.open,
            # so both entry points are guarded.
            with mock.patch("io.open", guarded_open), \
                    mock.patch("builtins.open", guarded_open):
                code, _ = run_main(["--repo-root", str(work)])
            self.assertEqual(code, 0)
            self.assertEqual(snapshot(work), before)
            observed = set()
            for raw in opened:
                try:
                    observed.add(str(Path(raw).relative_to(work)).replace("\\", "/"))
                except ValueError:
                    self.fail("verifier read outside repo root: %r" % (raw,))
            self.assertEqual(observed, EXPECTED_READS)
        finally:
            temporary.cleanup()

    def test_no_legacy_module_imports(self):
        source = (ROOT / "tools" / "field-survey" / "verify_fields.py").read_text(
            encoding="utf-8")
        for forbidden in ("import flask", "from flask", "jsonpatch",
                          "import get_game_config", "from get_game_config",
                          "import server", "from server", "import command",
                          "from command", "import engine", "from engine",
                          "import requests", "subprocess", "socket",
                          "urllib", "webbrowser", "http.server"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
