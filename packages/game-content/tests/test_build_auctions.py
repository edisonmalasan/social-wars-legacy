import ast
import contextlib
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packages" / "game-content" / "tools"))

import build_auctions as builder

SOURCE = ROOT / "packages" / "game-content" / "tools" / "build_auctions.py"
SCHEMA_PATH = ROOT / "packages" / "game-content" / "schemas" / "auction.schema.json"

EXPECTED_READS = frozenset([
    "config/auctionhouse.json",
    "auctions.py",
    "packages/game-content/schemas/auction.schema.json",
    "packages/game-content/normalized/units.json",
    "packages/game-content/manifest.json",
])

EXPECTED_WRITES = frozenset([
    "packages/game-content/normalized/auctions.json",
    "packages/game-content/manifest.json",
])

COMMITTED = [
    {"uuid": "1", "unit": 1167, "level": 1, "interval": 120,
     "price": 5000, "priceIncrement": 1000, "betPrice": 2},
    {"uuid": "2", "unit": 1168, "level": 1, "interval": 60,
     "price": 1000, "priceIncrement": 200, "betPrice": 2},
    {"uuid": "3", "unit": 1226, "level": 2, "interval": 120,
     "price": 8000, "priceIncrement": 1500, "betPrice": 2},
]

COMMITTED_UNIT_NAMES = {
    "1": "Blue Steel Bahamut",
    "2": "Blue Steel Draggy",
    "3": "Red Mercury Dragon",
}

BUILDER_SOURCE = SOURCE.read_text(encoding="utf-8")


def builder_code():
    """The builder's executable code, with docstrings and literals removed.

    Prose legitimately quotes the legacy conversion (``* 60``) and names
    ``os.makedirs`` in order to explain why neither appears in code, so a raw
    source scan would flag the documentation that documents the absence. Lines
    wholly covered by a string literal are dropped; the AST multiplication
    check below is the mechanically true form of the same claim, because it
    cannot be satisfied by a comment or a string.
    """
    covered = set()
    for node in ast.walk(ast.parse(BUILDER_SOURCE)):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            last = node.end_lineno or node.lineno
            covered.update(range(node.lineno, last + 1))
    return "\n".join(line for number, line
                     in enumerate(BUILDER_SOURCE.splitlines(), 1)
                     if number not in covered)


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
    (work / "config").mkdir(parents=True)
    shutil.copy2(ROOT / "config" / "auctionhouse.json",
                 work / "config" / "auctionhouse.json")
    shutil.copy2(ROOT / "auctions.py", work / "auctions.py")
    (work / "packages" / "game-content" / "schemas").mkdir(parents=True)
    shutil.copy2(SCHEMA_PATH,
                 work / "packages" / "game-content" / "schemas"
                 / "auction.schema.json")
    (work / "packages" / "game-content" / "normalized").mkdir(parents=True)
    shutil.copy2(ROOT / "packages" / "game-content" / "normalized" / "units.json",
                 work / "packages" / "game-content" / "normalized" / "units.json")
    shutil.copy2(ROOT / "packages" / "game-content" / "manifest.json",
                 work / "packages" / "game-content" / "manifest.json")
    return temporary, work


def read_work_json(work, relative):
    return json.loads((work / relative).read_text(encoding="utf-8"))


def write_work_auctions(work, entries):
    (work / "config" / "auctionhouse.json").write_text(
        json.dumps({"auctions": entries}), encoding="utf-8")


class CommittedSourceTests(unittest.TestCase):
    """The committed table itself, read rather than restated."""

    def test_source_is_the_standalone_file(self):
        self.assertTrue((ROOT / "config" / "auctionhouse.json").is_file())
        self.assertEqual(
            builder.AUCTION_CONFIG_FILE.as_posix(),
            "config/auctionhouse.json")
        # Not one of the 20 top-level keys of config/main.json.
        main = json.loads((ROOT / "config" / "main.json").read_text(
            encoding="utf-8"))
        self.assertNotIn("auctions", main)

    def test_committed_table_shape(self):
        document = json.loads((ROOT / "config" / "auctionhouse.json").read_text(
            encoding="utf-8"))
        self.assertEqual(sorted(document.keys()), ["auctions"])
        self.assertEqual(document["auctions"], COMMITTED)
        self.assertEqual(len(document["auctions"]), 3)

    def test_every_entry_carries_exactly_the_seven_committed_keys(self):
        document = json.loads((ROOT / "config" / "auctionhouse.json").read_text(
            encoding="utf-8"))
        for entry in document["auctions"]:
            self.assertEqual(set(entry.keys()), set(builder.AUCTION_FIELDS))
            self.assertEqual(len(entry), 7)

    def test_uuid_is_declared_quoted_in_the_source_text(self):
        text = (ROOT / "config" / "auctionhouse.json").read_text(
            encoding="utf-8")
        self.assertEqual(text.count('"uuid": "'), 3)


class LayeringTests(unittest.TestCase):
    """This table carries no patch layering and no mods pipeline."""

    @classmethod
    def setUpClass(cls):
        cls.layers = builder.load_all(str(ROOT))

    def test_source_layer_is_stored(self):
        self.assertEqual(builder.SOURCE_LAYER, "stored")

    def test_three_stored_auctions_loaded(self):
        self.assertEqual(len(self.layers["stored_auctions"]), 3)

    def test_no_main_json_or_patch_or_mods_read(self):
        # Structural rather than observational: the builder declares no path
        # constant for any of them, and the containment test pins the read
        # set to exactly five files.
        constants = [value for name, value in vars(builder).items()
                     if isinstance(value, Path)]
        for value in constants:
            self.assertNotIn("patch", value.parts)
            self.assertNotIn("mods", value.parts)
        self.assertEqual(len(constants), len(set(constants)))
        source_paths = re.findall(r"Path\(\"([a-z_]+)\"\)", BUILDER_SOURCE)
        for forbidden in ("patch", "mods"):
            self.assertNotIn(forbidden, source_paths)

    def test_units_reference_edge_is_the_units_file_alone(self):
        self.assertEqual(builder.UNITS_FILE.as_posix(),
                         "packages/game-content/normalized/units.json")
        self.assertEqual(self.layers["units_counts"], {"units": 429})
        self.assertEqual(len(self.layers["unit_names"]), 429)


class VerbatimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layers = builder.load_all(str(ROOT))
        cls.first = builder.coerce_auction(cls.layers["stored_auctions"][0],
                                           "auction uuid '1'")

    def test_committed_values_verbatim(self):
        self.assertEqual(self.first, COMMITTED[0])

    def test_uuid_stays_a_committed_string(self):
        self.assertIs(type(self.first["uuid"]), str)
        self.assertEqual(self.first["uuid"], "1")

    def test_committed_numbers_stay_native_ints(self):
        for field in ("unit", "level", "interval", "price", "priceIncrement",
                      "betPrice"):
            self.assertIs(type(self.first[field]), int, field)

    def test_rejects_integer_uuid(self):
        mutated = dict(self.layers["stored_auctions"][0])
        mutated["uuid"] = 1
        with self.assertRaises(builder.ValidationFailure) as caught:
            builder.coerce_auction(mutated, "mutated")
        self.assertIn("A1", " ".join(caught.exception.problems))

    def test_rejects_empty_uuid(self):
        mutated = dict(self.layers["stored_auctions"][0])
        mutated["uuid"] = ""
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_auction(mutated, "mutated")

    def test_rejects_bool_amount(self):
        for field in ("unit", "level", "interval", "price", "priceIncrement",
                      "betPrice"):
            mutated = dict(self.layers["stored_auctions"][0])
            mutated[field] = True
            with self.assertRaises(builder.ValidationFailure, msg=field):
                builder.coerce_auction(mutated, "mutated")

    def test_rejects_string_amount(self):
        mutated = dict(self.layers["stored_auctions"][0])
        mutated["interval"] = "120"
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_auction(mutated, "mutated")

    def test_rejects_missing_and_unexpected_fields(self):
        mutated = dict(self.layers["stored_auctions"][0])
        del mutated["betPrice"]
        with self.assertRaises(builder.ValidationFailure) as caught:
            builder.coerce_auction(mutated, "mutated")
        self.assertIn("missing", " ".join(caught.exception.problems))
        mutated = dict(self.layers["stored_auctions"][0])
        mutated["invented"] = 1
        with self.assertRaises(builder.ValidationFailure) as caught:
            builder.coerce_auction(mutated, "mutated")
        self.assertIn("unexpected", " ".join(caught.exception.problems))

    def test_rejects_non_object_entry(self):
        with self.assertRaises(builder.ValidationFailure):
            builder.coerce_auction(["1"], "mutated")


class IntervalTests(unittest.TestCase):
    """Rule A2: interval is preserved in minutes and never converted."""

    @classmethod
    def setUpClass(cls):
        cls.section, cls.payloads = builder.build_package(str(ROOT), str(ROOT))
        cls.auctions = json.loads(cls.payloads[builder.AUCTIONS_FILE])
        cls.text = cls.payloads[builder.AUCTIONS_FILE]

    def test_committed_minutes_verbatim(self):
        self.assertEqual([item["interval"] for item in self.auctions],
                         [120, 60, 120])
        self.assertEqual(self.section["counts"]["intervals"], [60, 120])
        self.assertEqual(self.section["counts"]["interval_unit"], "minutes")

    def test_unit_label_is_minutes(self):
        for item in self.auctions:
            self.assertEqual(item["interval_unit"], "minutes")

    def test_no_seconds_or_duration_field_exists(self):
        forbidden = ("seconds", "duration", "interval_seconds", "interval_s")
        for item in self.auctions:
            for field in item:
                self.assertNotIn(field, forbidden, field)

    def test_conversion_factor_is_not_recorded_as_data(self):
        # The factor 60 appears in the committed table as uuid "2"'s own
        # interval, so the claim is scoped to data, not to the number: the
        # normalized payload must never contain the multiplication, and the
        # note must state that no conversion was performed here.
        self.assertNotIn("* 60", self.text)
        self.assertNotIn("*60", self.text)
        notes = " ".join(self.section["notes"])
        self.assertIn("not", notes)
        self.assertIn("belong", notes)
        self.assertIn("interval", notes)

    def test_builder_source_multiplies_by_sixty_nowhere(self):
        # The one conversion the legacy module performs (auctions.py:76) is
        # deliberately absent from the builder. The prose has to quote it in
        # order to say so, so the claim is made over the code: no AST
        # multiplication node in the builder has 60 as an operand. A string or
        # comment cannot satisfy this.
        for node in ast.walk(ast.parse(BUILDER_SOURCE)):
            if not isinstance(node, ast.BinOp):
                continue
            if not isinstance(node.op, ast.Mult):
                continue
            self.assertNotEqual(
                getattr(node.right, "value", None), 60,
                "multiplication by 60 at build_auctions.py:%d" % node.lineno)
        self.assertNotIn("* 60", builder_code())
        self.assertNotIn("*60", builder_code())


class ResolutionTests(unittest.TestCase):
    """Rule A3: units resolve; an unresolved id is recorded, never dropped."""

    @classmethod
    def setUpClass(cls):
        cls.layers = builder.load_all(str(ROOT))
        cls.section, cls.payloads = builder.build_package(str(ROOT), str(ROOT))
        cls.auctions = json.loads(cls.payloads[builder.AUCTIONS_FILE])

    def test_all_three_committed_units_resolve(self):
        self.assertEqual([item["unit_name"] for item in self.auctions],
                         ["Blue Steel Bahamut", "Blue Steel Draggy",
                          "Red Mercury Dragon"])
        self.assertEqual(
            {item["legacy_id"]: item["unit_name"]
             for item in self.auctions},
            COMMITTED_UNIT_NAMES)
        self.assertTrue(all(item["unit_resolved"] for item in self.auctions))
        self.assertEqual(self.section["counts"]["resolved_units"], 3)
        self.assertEqual(self.section["counts"]["unresolved_units"], 0)
        self.assertEqual(self.section["reported"], [])

    def test_unit_ref_is_the_decimal_form_and_resolves(self):
        for item in self.auctions:
            self.assertEqual(item["unit_ref"], str(item["unit"]))
            self.assertIn(item["unit_ref"], self.layers["unit_names"])

    def test_the_edges_name_committed_endgame_units(self):
        for item in self.auctions:
            self.assertGreaterEqual(item["unit"], 923)

    def test_unresolved_unit_is_emitted_in_order_and_reported(self):
        temporary, work = make_work_tree()
        self.addCleanup(temporary.cleanup)
        entries = [dict(entry) for entry in COMMITTED]
        entries[1]["unit"] = 999999
        write_work_auctions(work, entries)
        code, stdout, stderr = run_main(["--repo-root", str(work),
                                         "--out-root", str(work)])
        self.assertEqual(code, 0, stderr)
        report = json.loads(stdout)
        self.assertEqual(report["result"], "success")
        written = read_work_json(
            work, "packages/game-content/normalized/auctions.json")
        self.assertEqual([item["legacy_id"] for item in written],
                         ["1", "2", "3"])
        unresolved = written[1]
        self.assertEqual(unresolved["unit"], 999999)
        self.assertEqual(unresolved["unit_ref"], "999999")
        self.assertFalse(unresolved["unit_resolved"])
        self.assertIsNone(unresolved["unit_name"])
        self.assertEqual(len(report["reported"]), 1)
        self.assertIn("999999", report["reported"][0])
        self.assertIn("unresolved", report["reported"][0])
        section = read_work_json(
            work, "packages/game-content/manifest.json")["auctions"]
        self.assertEqual(section["counts"]["unresolved_units"], 1)
        self.assertEqual(section["validation"]["unresolved_unit_references"],
                         1)
        self.assertEqual(len(section["reported"]), 1)

    def test_unresolved_entry_is_not_dropped_or_replaced(self):
        # The definition count is a pure function of the committed table, so
        # a broken reference cannot change it.
        temporary, work = make_work_tree()
        self.addCleanup(temporary.cleanup)
        entries = [dict(entry) for entry in COMMITTED]
        for entry in entries:
            entry["unit"] = 999999
        write_work_auctions(work, entries)
        code, _, stderr = run_main(["--repo-root", str(work),
                                    "--out-root", str(work)])
        self.assertEqual(code, 0, stderr)
        written = read_work_json(
            work, "packages/game-content/normalized/auctions.json")
        self.assertEqual(len(written), 3)
        self.assertEqual([item["unit"] for item in written],
                         [999999, 999999, 999999])
        self.assertTrue(all(item["unit_name"] is None for item in written))
        self.assertTrue(all(item["unit_resolved"] is False
                            for item in written))


class BetPriceTests(unittest.TestCase):
    """Rule A4: betPrice is carried and marked unconsumed, by measurement."""

    @classmethod
    def setUpClass(cls):
        cls.layers = builder.load_all(str(ROOT))
        cls.consumption = cls.layers["consumption"]
        cls.section, cls.payloads = builder.build_package(str(ROOT), str(ROOT))
        cls.auctions = json.loads(cls.payloads[builder.AUCTIONS_FILE])

    def test_bet_price_carried_verbatim_on_every_entry(self):
        self.assertEqual([item["betPrice"] for item in self.auctions],
                         [2, 2, 2])
        self.assertEqual(self.section["counts"]["bet_prices"], [2])

    def test_bet_price_consumed_false_on_every_entry(self):
        for item in self.auctions:
            self.assertIs(item["bet_price_consumed"], False)
        self.assertEqual(self.section["validation"]["bet_price_consumers"], 0)

    def test_every_listed_resource_token_has_zero_whole_token_hits(self):
        whole = self.consumption["resource_tokens_whole_token"]
        self.assertEqual(sorted(whole), sorted(builder.BET_PRICE_RESOURCE_TOKENS))
        for token in builder.BET_PRICE_RESOURCE_TOKENS:
            self.assertEqual(whole[token], 0, token)

    def test_apply_resources_is_never_called(self):
        self.assertFalse(self.consumption["apply_resources_called"])
        # The measurement records the COUNT of distinct self-calls, so the
        # method names are re-derived here from the committed module text and
        # the recorded count is checked against them.
        module_text = (ROOT / "auctions.py").read_text(encoding="utf-8")
        called = sorted(set(re.findall(
            r"self\.([A-Za-z_][A-Za-z0-9_]*)\s*\(", module_text)))
        self.assertEqual(self.consumption["self_called_methods"], len(called))
        self.assertNotIn("apply_resources", called)

    def test_substring_artifacts_are_recorded_beside_the_whole_token_count(self):
        # xp has three substring hits and zero whole-token hits; a
        # substring-only scan would report a consumer that does not exist.
        substring = self.consumption["resource_tokens_substring"]
        artifacts = self.consumption["resource_token_substring_artifacts"]
        self.assertEqual(substring["xp"], 3)
        self.assertEqual(self.consumption["resource_tokens_whole_token"]["xp"], 0)
        self.assertEqual(artifacts["xp"], ["count_expired", "expired"])
        for token in builder.BET_PRICE_RESOURCE_TOKENS:
            if token != "xp":
                self.assertEqual(substring[token], 0, token)
                self.assertNotIn(token, artifacts)

    def test_measurement_is_re_derived_from_the_module_not_asserted(self):
        module_text = (ROOT / "auctions.py").read_text(encoding="utf-8")
        fresh = builder.measure_bet_price_consumers(module_text)
        self.assertEqual(fresh, self.consumption)
        # And it fails closed: an injected consumer flips the flag.
        poisoned = builder.measure_bet_price_consumers(
            module_text + "\napply_resources(save, {\"gold\": 1})\n")
        self.assertTrue(poisoned["consumed"])
        self.assertEqual(poisoned["resource_tokens_whole_token"]["gold"], 1)

    def test_write_sites_are_cited(self):
        self.assertEqual(list(builder.BET_PRICE_WRITE_SITES),
                         ["auctions.py:97", "auctions.py:137"])
        module_lines = (ROOT / "auctions.py").read_text(
            encoding="utf-8").splitlines()
        for line_number in (97, 137):
            self.assertIn('"betPrice"', module_lines[line_number - 1],
                          "auctions.py:" + str(line_number))
        # The two sites are not the same statement: line 97 builds the state
        # document and line 137 updates an existing bet, so each is pinned by
        # its own text rather than by a shared substring.
        self.assertEqual(
            module_lines[96].strip(), '"betPrice": auction["betPrice"],')
        self.assertEqual(
            module_lines[136].strip(),
            'bet["betPrice"] = auction["betPrice"]')
        # Each site names the key twice (once as the written key, once as the
        # committed source read), so the totals are 2 reads and 4 mentions --
        # which is what makes "written at two sites and read nowhere" a
        # countable claim rather than a citation.
        module_text = (ROOT / "auctions.py").read_text(encoding="utf-8")
        self.assertEqual(module_text.count('auction["betPrice"]'), 2)
        self.assertEqual(module_text.count('"betPrice"'), 4)
        # The four mentions are two write keys and two reads of the COMMITTED
        # value; no expression reads a stored betPrice back out of the state
        # document, which is what the zero-consumer record claims. Each
        # occurrence is classified by the text that introduces it.
        kinds = {"committed read": 0, "written key": 0, "other": []}
        for match in re.finditer("betPrice", module_text):
            tail = module_text[:match.start()]
            if tail.endswith('auction["'):
                kinds["committed read"] += 1
            elif tail.endswith('["') or tail.endswith('"'):
                kinds["written key"] += 1
            else:
                kinds["other"].append(tail[-40:])
        self.assertEqual(kinds["other"], [])
        self.assertEqual(kinds["committed read"], 2)
        self.assertEqual(kinds["written key"], 2)

    def test_manifest_cites_the_measurement_rather_than_a_verdict(self):
        record = self.section["inputs"]["legacy_module_measurement"]
        self.assertFalse(record["imported"])
        self.assertFalse(record["executed"])
        self.assertTrue(record["read_as_text_only"])
        self.assertEqual(record["file"], "auctions.py")
        self.assertIn("counting_rule", record)
        self.assertIn("substring", record["counting_rule"])
        self.assertEqual(record["bet_price_write_sites"],
                         ["auctions.py:97", "auctions.py:137"])


class ManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.section, cls.payloads = builder.build_package(str(ROOT), str(ROOT))

    def test_manifest_matches_produced_output(self):
        temporary, work = make_work_tree()
        try:
            code, _, _ = run_main(["--repo-root", str(work),
                                   "--out-root", str(work)])
            self.assertEqual(code, 0)
            manifest = read_work_json(work, "packages/game-content/manifest.json")
            self.assertIn("auctions", manifest)
            section = manifest["auctions"]
            self.assertEqual(section["result"], "success")
            self.assertEqual(section["policy"], builder.POLICY)
            self.assertEqual(section["coercion_ruleset"],
                             builder.COERCION_RULESET_VERSION)
            auctions = read_work_json(
                work, "packages/game-content/normalized/auctions.json")
            self.assertEqual(section["counts"]["auctions"], len(auctions))
            self.assertEqual(section["counts"]["auctions"], 3)
            by_file = {entry["file"]: entry for entry in section["outputs"]}
            self.assertEqual(set(by_file),
                             set(EXPECTED_WRITES)
                             - {"packages/game-content/manifest.json"})
            data = (work / "packages" / "game-content" / "normalized"
                    / "auctions.json").read_bytes()
            self.assertEqual(
                by_file["packages/game-content/normalized/auctions.json"]["bytes"],
                len(data))
            self.assertEqual(
                by_file["packages/game-content/normalized/auctions.json"]["sha256"],
                hashlib.sha256(data).hexdigest())
            self.assertTrue(section["notes"])
            self.assertEqual(section["content_fingerprint"],
                             builder.fingerprint_inputs(
                                 builder.load_all(str(work))))
            self.assertEqual(
                section["inputs"]["units_reference_edge"]["union_legacy_ids"],
                429)
            self.assertEqual(section["inputs"]["auctionhouse"]["file"],
                             "config/auctionhouse.json")
        finally:
            temporary.cleanup()

    def test_content_source_is_the_standalone_file(self):
        source = self.section["inputs"]["content_source"]
        self.assertIn("standalone", source)
        self.assertIn("20 top-level keys", source)
        for item in json.loads(self.payloads[builder.AUCTIONS_FILE]):
            self.assertEqual(item["source_file"], "config/auctionhouse.json")
            self.assertEqual(item["source_layer"], "stored")

    def test_every_prior_manifest_section_survives_untouched(self):
        temporary, work = make_work_tree()
        try:
            # The committed manifest already carries the auctions section this
            # builder merges, so it is removed first: the claim under test is
            # that a merge ADDS exactly that key and changes no prior byte, not
            # that it adds a key it already found.
            manifest_path = work / "packages/game-content/manifest.json"
            stripped = read_work_json(work, "packages/game-content/manifest.json")
            self.assertIn("auctions", stripped)
            del stripped["auctions"]
            manifest_path.write_text(
                json.dumps(stripped, indent=2, sort_keys=True) + "\n",
                encoding="utf-8")
            before = read_work_json(work, "packages/game-content/manifest.json")
            self.assertNotIn("auctions", before)
            code, _, _ = run_main(["--repo-root", str(work),
                                   "--out-root", str(work)])
            self.assertEqual(code, 0)
            after = read_work_json(work, "packages/game-content/manifest.json")
            self.assertEqual(sorted(set(after) - set(before)), ["auctions"])
            self.assertEqual(sorted(set(before) - set(after)), [])
            for key in sorted(set(before) & set(after)):
                self.assertEqual(after[key], before[key], key)
        finally:
            temporary.cleanup()

    def test_committed_manifest_prior_sections_are_byte_identical(self):
        # The merge re-serializes the whole document with sort_keys, so a
        # prior section changing would mean the working manifest drifted from
        # its committed form for a reason other than the new section.
        import subprocess
        committed = json.loads(subprocess.check_output(
            ["git", "show", "HEAD:packages/game-content/manifest.json"]
        ).decode("utf-8"))
        current = json.loads((ROOT / "packages" / "game-content"
                              / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(set(current) - set(committed)), ["auctions"])
        for key in sorted(set(committed)):
            self.assertEqual(current[key], committed[key], key)


class TraceabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _section, payloads = builder.build_package(str(ROOT), str(ROOT))
        cls.auction_schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.auction = json.loads(payloads[builder.AUCTIONS_FILE])[0]

    def test_required_is_subset_of_properties(self):
        for field in self.auction_schema["required"]:
            self.assertIn(field, self.auction_schema["properties"],
                          "required not in properties: " + field)

    def test_every_required_field_is_enforced(self):
        for field in self.auction_schema["required"]:
            mutated = dict(self.auction)
            del mutated[field]
            problems = builder.validate_against_schema(
                mutated, self.auction_schema,
                "auction " + self.auction["legacy_id"])
            self.assertTrue(
                any("missing required field" in problem and field in problem
                    for problem in problems),
                "no validator check for required field auction.%s" % (field,))

    def test_wrong_types_are_rejected(self):
        cases = [("legacy_id", 1), ("uuid", 1), ("unit", "1167"),
                 ("unit_ref", 1167), ("unit_name", 7), ("unit_resolved", 1),
                 ("level", "1"), ("interval", "120"), ("interval_unit", "seconds"),
                 ("price", "5000"), ("priceIncrement", "1000"),
                 ("betPrice", "2"), ("bet_price_consumed", True),
                 ("kind", "auctions"), ("source_file", "config/main.json"),
                 ("source_layer", "patched"), ("content_version", 1),
                 ("content_version", None)]
        for field, bad in cases:
            mutated = dict(self.auction)
            mutated[field] = bad
            problems = builder.validate_against_schema(
                mutated, self.auction_schema,
                "auction " + self.auction["legacy_id"])
            self.assertTrue(problems,
                            "no check for auction.%s = %r" % (field, bad))

    def test_null_unit_name_is_accepted(self):
        mutated = dict(self.auction)
        mutated["unit_name"] = None
        self.assertEqual(
            builder.validate_against_schema(
                mutated, self.auction_schema, "auction"), [])

    def test_minimum_gates_enforced(self):
        for field in ("unit", "level", "interval", "price", "priceIncrement",
                      "betPrice"):
            mutated = dict(self.auction)
            mutated[field] = -1
            self.assertTrue(builder.validate_against_schema(
                mutated, self.auction_schema, "auction"), field)

    def test_no_extra_properties(self):
        mutated = dict(self.auction)
        mutated["seconds"] = 7200
        problems = builder.validate_against_schema(
            mutated, self.auction_schema, "auction")
        self.assertTrue(any("additional property" in problem
                            for problem in problems))

    def test_ruleset_lists_every_committed_field(self):
        ruleset = self.auction_schema["x-coercion-ruleset"]
        self.assertEqual(ruleset["version"], builder.COERCION_RULESET_VERSION)
        listed = {rule["committed_field"] for rule in ruleset["rules"]}
        self.assertEqual(sorted(listed), sorted(builder.AUCTION_FIELDS))

    def test_every_ruleset_rule_names_a_real_property(self):
        for rule in self.auction_schema["x-coercion-ruleset"]["rules"]:
            self.assertIn(rule["normalized_field"],
                          self.auction_schema["properties"], rule)
            self.assertTrue(rule["transform"])
            self.assertTrue(rule["note"])

    def test_every_non_rule_property_has_a_named_derivation(self):
        ruleset = self.auction_schema["x-coercion-ruleset"]
        targeted = {rule["normalized_field"] for rule in ruleset["rules"]}
        for field in self.auction_schema["properties"]:
            if field in targeted:
                self.assertNotIn(field, ruleset["non_committed_fields"], field)
                continue
            self.assertIn(field, ruleset["non_committed_fields"], field)
            self.assertTrue(ruleset["non_committed_fields"][field]["derivation"])

    def test_ruleset_gate_rejects_an_unlisted_committed_field(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        schema["x-coercion-ruleset"]["rules"] = [
            rule for rule in schema["x-coercion-ruleset"]["rules"]
            if rule["committed_field"] != "betPrice"]
        with self.assertRaises(builder.InputError) as caught:
            builder.validate_coercion_ruleset(schema, "auction.schema.json")
        self.assertIn("betPrice", str(caught.exception))

    def test_ruleset_gate_rejects_an_unlisted_derived_property(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        schema["properties"]["invented_helper"] = {"type": "string"}
        with self.assertRaises(builder.InputError) as caught:
            builder.validate_coercion_ruleset(schema, "auction.schema.json")
        self.assertIn("no listed derivation", str(caught.exception))

    def test_ruleset_gate_rejects_an_uncommitted_source_field(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        schema["x-coercion-ruleset"]["rules"][0]["committed_field"] = "gold"
        with self.assertRaises(builder.InputError) as caught:
            builder.validate_coercion_ruleset(schema, "auction.schema.json")
        self.assertIn("uncommitted field", str(caught.exception))

    def test_ruleset_gate_rejects_a_version_mismatch(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        schema["x-coercion-ruleset"]["version"] = "something-else"
        with self.assertRaises(builder.InputError):
            builder.validate_coercion_ruleset(schema, "auction.schema.json")


class RoundTripTests(unittest.TestCase):
    def test_round_trip_clean_on_real_content(self):
        layers = builder.load_all(str(ROOT))
        _section, payloads = builder.build_package(str(ROOT), str(ROOT))
        auctions = json.loads(payloads[builder.AUCTIONS_FILE])
        self.assertEqual(
            builder.check_round_trip(auctions, layers["stored_auctions"]), [])

    def test_round_trip_covers_all_seven_keys_on_all_three_entries(self):
        layers = builder.load_all(str(ROOT))
        _section, payloads = builder.build_package(str(ROOT), str(ROOT))
        auctions = json.loads(payloads[builder.AUCTIONS_FILE])
        self.assertEqual(len(auctions), 3)
        covered = 0
        for definition, original in zip(auctions, layers["stored_auctions"]):
            for field in builder.AUCTION_FIELDS:
                self.assertEqual(original[field], definition[field])
                covered += 1
        self.assertEqual(covered, 7 * 3)

    def test_round_trip_is_exact_against_the_committed_document(self):
        committed = json.loads((ROOT / "config" / "auctionhouse.json").read_text(
            encoding="utf-8"))["auctions"]
        _section, payloads = builder.build_package(str(ROOT), str(ROOT))
        auctions = json.loads(payloads[builder.AUCTIONS_FILE])
        self.assertEqual(auctions, [
            {
                "legacy_id": entry["uuid"],
                "kind": "auction",
                "source_file": "config/auctionhouse.json",
                "source_layer": "stored",
                "content_version": auctions[0]["content_version"],
                "uuid": entry["uuid"],
                "unit": entry["unit"],
                "unit_ref": str(entry["unit"]),
                "unit_name": COMMITTED_UNIT_NAMES[entry["uuid"]],
                "unit_resolved": True,
                "level": entry["level"],
                "interval": entry["interval"],
                "interval_unit": "minutes",
                "price": entry["price"],
                "priceIncrement": entry["priceIncrement"],
                "betPrice": entry["betPrice"],
                "bet_price_consumed": False,
            }
            for entry in committed])

    def test_round_trip_detects_a_drifted_definition(self):
        layers = builder.load_all(str(ROOT))
        _section, payloads = builder.build_package(str(ROOT), str(ROOT))
        auctions = json.loads(payloads[builder.AUCTIONS_FILE])
        for field, bad in (("interval", 60), ("price", 0), ("level", 99),
                           ("unit", 1), ("betPrice", 0), ("priceIncrement", 0),
                           ("uuid", "9")):
            mutated = [dict(entry) for entry in auctions]
            mutated[0][field] = bad
            problems = builder.check_round_trip(mutated,
                                               layers["stored_auctions"])
            self.assertTrue(problems, field)

    def test_round_trip_detects_a_count_mismatch(self):
        layers = builder.load_all(str(ROOT))
        _section, payloads = builder.build_package(str(ROOT), str(ROOT))
        auctions = json.loads(payloads[builder.AUCTIONS_FILE])
        problems = builder.check_round_trip(auctions[:-1],
                                           layers["stored_auctions"])
        self.assertTrue(any("count mismatch" in problem
                            for problem in problems))


class ValidationFailureTests(unittest.TestCase):
    def setUp(self):
        self.temporary, self.work = make_work_tree()
        self.addCleanup(self.temporary.cleanup)

    def build(self):
        return run_main(["--repo-root", str(self.work),
                         "--out-root", str(self.work)])

    def test_clean_work_tree_build_exit_0(self):
        code, stdout, stderr = self.build()
        self.assertEqual(code, 0, stderr)
        report = json.loads(stdout)
        self.assertEqual(report["result"], "success")
        self.assertEqual(report["counts"]["auctions"], 3)
        self.assertEqual(report["reported"], [])

    def test_duplicate_uuid_exit_1(self):
        entries = [dict(entry) for entry in COMMITTED]
        entries[2]["uuid"] = "1"
        write_work_auctions(self.work, entries)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("duplicate", " ".join(json.loads(stdout)["problems"]))

    def test_integer_uuid_exit_1(self):
        entries = [dict(entry) for entry in COMMITTED]
        entries[0]["uuid"] = 1
        write_work_auctions(self.work, entries)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("A1", " ".join(json.loads(stdout)["problems"]))

    def test_missing_field_exit_1(self):
        entries = [dict(entry) for entry in COMMITTED]
        del entries[0]["betPrice"]
        write_work_auctions(self.work, entries)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("missing", " ".join(json.loads(stdout)["problems"]))

    def test_extra_field_exit_1(self):
        entries = [dict(entry) for entry in COMMITTED]
        entries[0]["round"] = 1
        write_work_auctions(self.work, entries)
        code, stdout, _ = self.build()
        self.assertEqual(code, 1)
        self.assertIn("unexpected", " ".join(json.loads(stdout)["problems"]))

    def test_failure_writes_nothing(self):
        before_manifest = (self.work / "packages" / "game-content"
                           / "manifest.json").read_bytes()
        entries = [dict(entry) for entry in COMMITTED]
        del entries[0]["level"]
        write_work_auctions(self.work, entries)
        code, _, _ = self.build()
        self.assertEqual(code, 1)
        self.assertFalse((self.work / "packages" / "game-content" / "normalized"
                          / "auctions.json").exists())
        self.assertEqual((self.work / "packages" / "game-content"
                          / "manifest.json").read_bytes(), before_manifest)

    def test_extra_top_level_key_exit_2(self):
        (self.work / "config" / "auctionhouse.json").write_text(
            json.dumps({"auctions": COMMITTED, "extra": 1}), encoding="utf-8")
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("expected exactly", stderr)

    def test_non_object_top_level_exit_2(self):
        (self.work / "config" / "auctionhouse.json").write_text(
            json.dumps(COMMITTED), encoding="utf-8")
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("top level not object", stderr)

    def test_empty_auctions_array_exit_2(self):
        (self.work / "config" / "auctionhouse.json").write_text(
            json.dumps({"auctions": []}), encoding="utf-8")
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("not non-empty array", stderr)

    def test_unparseable_config_exit_2(self):
        (self.work / "config" / "auctionhouse.json").write_text("{broken",
                                                                 encoding="utf-8")
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("not valid json", stderr)

    def test_missing_config_exit_2(self):
        (self.work / "config" / "auctionhouse.json").unlink()
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("auction config file missing", stderr)

    def test_missing_units_edge_exit_2(self):
        (self.work / "packages" / "game-content" / "normalized"
         / "units.json").unlink()
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("normalized units", stderr)

    def test_missing_legacy_module_exit_2(self):
        (self.work / "auctions.py").unlink()
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("legacy auction module file missing", stderr)

    def test_missing_schema_exit_2(self):
        (self.work / "packages" / "game-content" / "schemas"
         / "auction.schema.json").unlink()
        code, _, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("schema auction file missing", stderr)
        self.assertIn("auction.schema.json", stderr)

    def test_bad_repo_root_exit_2(self):
        code, _, stderr = run_main(["--repo-root",
                                    str(self.work / "does-not-exist")])
        self.assertEqual(code, 2)
        self.assertIn("repository root invalid", stderr)


class IdempotenceTests(unittest.TestCase):
    def test_repeated_work_tree_builds_byte_identical(self):
        temporary, work = make_work_tree()
        self.addCleanup(temporary.cleanup)
        code, _, _ = run_main(["--repo-root", str(work), "--out-root", str(work)])
        self.assertEqual(code, 0)
        first = {name: (work / name).read_bytes() for name in EXPECTED_WRITES}
        code, _, _ = run_main(["--repo-root", str(work), "--out-root", str(work)])
        self.assertEqual(code, 0)
        for name, payload in first.items():
            self.assertEqual((work / name).read_bytes(), payload, name)

    def test_third_build_still_identical(self):
        temporary, work = make_work_tree()
        self.addCleanup(temporary.cleanup)
        digests = []
        for _ in range(3):
            code, _, _ = run_main(["--repo-root", str(work),
                                   "--out-root", str(work)])
            self.assertEqual(code, 0)
            digests.append({
                name: hashlib.sha256((work / name).read_bytes()).hexdigest()
                for name in EXPECTED_WRITES})
        self.assertEqual(digests[0], digests[1])
        self.assertEqual(digests[1], digests[2])

    def test_manifest_section_is_stable_across_runs(self):
        temporary, work = make_work_tree()
        self.addCleanup(temporary.cleanup)
        sections = []
        for _ in range(2):
            code, _, _ = run_main(["--repo-root", str(work),
                                   "--out-root", str(work)])
            self.assertEqual(code, 0)
            sections.append(json.dumps(
                read_work_json(work, "packages/game-content/manifest.json")["auctions"],
                sort_keys=True))
        self.assertEqual(sections[0], sections[1])

    def test_committed_output_matches_a_fresh_build(self):
        temporary, work = make_work_tree()
        self.addCleanup(temporary.cleanup)
        code, _, _ = run_main(["--repo-root", str(work), "--out-root", str(work)])
        self.assertEqual(code, 0)
        committed = (ROOT / "packages" / "game-content" / "normalized"
                     / "auctions.json").read_bytes()
        rebuilt = (work / "packages" / "game-content" / "normalized"
                   / "auctions.json").read_bytes()
        self.assertEqual(rebuilt, committed)
        self.assertEqual(
            hashlib.sha256(committed).hexdigest(),
            json.loads((ROOT / "packages" / "game-content" / "manifest.json"
                        ).read_text(encoding="utf-8"))["auctions"]["outputs"][0]["sha256"])


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
            code, _, stderr, opened, before = self.guarded_run(
                work, ["--repo-root", str(work), "--out-root", str(work)])
            self.assertEqual(code, 0, stderr)
            reads, writes = self.observed_sets(work, opened)
            self.assertEqual(reads, set(EXPECTED_READS))
            self.assertEqual(writes, set(EXPECTED_WRITES))
            after = snapshot(work)
            new_files = {path for path in set(after) - set(before)
                         if after[path] != "directory"}
            self.assertEqual(
                new_files,
                {"packages/game-content/normalized/auctions.json"})
            for path, payload in before.items():
                if path == "packages/game-content/manifest.json":
                    continue
                self.assertEqual(after[path], payload, path)
        finally:
            temporary.cleanup()

    def test_failure_writes_nothing_and_inputs_unchanged(self):
        temporary, work = make_work_tree()
        try:
            entries = [dict(entry) for entry in COMMITTED]
            del entries[0]["price"]
            write_work_auctions(work, entries)
            code, _, _, opened, before = self.guarded_run(
                work, ["--repo-root", str(work), "--out-root", str(work)])
            self.assertEqual(code, 1)
            _reads, writes = self.observed_sets(work, opened)
            self.assertEqual(writes, set())
            self.assertEqual(snapshot(work), before)
        finally:
            temporary.cleanup()

    def test_build_creates_no_auctions_state_directory(self):
        # The containment property this surface exists to protect: importing
        # or executing the legacy module would create auctions/ relative to
        # the process cwd.
        temporary, work = make_work_tree()
        try:
            code, _, stderr = run_main(["--repo-root", str(work),
                                        "--out-root", str(work)])
            self.assertEqual(code, 0, stderr)
            self.assertFalse((work / "auctions").exists())
            self.assertFalse((work / "auctions.json").exists())
            self.assertFalse((work / "saves").exists())
            directories = {path for path, value in snapshot(work).items()
                           if value == "directory"}
            self.assertNotIn("auctions", directories)
            self.assertEqual(
                sorted(directories),
                ["config", "packages", "packages/game-content",
                 "packages/game-content/normalized",
                 "packages/game-content/schemas"])
        finally:
            temporary.cleanup()

    def test_repository_root_has_no_auctions_directory(self):
        self.assertFalse((ROOT / "auctions").exists())
        self.assertFalse((ROOT / "auctions.json").exists())
        builder.build_package(str(ROOT), str(ROOT))
        self.assertFalse((ROOT / "auctions").exists())

    def test_committed_source_bytes_are_never_written(self):
        temporary, work = make_work_tree()
        try:
            config = work / "config" / "auctionhouse.json"
            module = work / "auctions.py"
            before_config = hashlib.sha256(config.read_bytes()).hexdigest()
            before_module = hashlib.sha256(module.read_bytes()).hexdigest()
            code, _, _ = run_main(["--repo-root", str(work),
                                   "--out-root", str(work)])
            self.assertEqual(code, 0)
            self.assertEqual(hashlib.sha256(config.read_bytes()).hexdigest(),
                             before_config)
            self.assertEqual(hashlib.sha256(module.read_bytes()).hexdigest(),
                             before_module)
            self.assertEqual(before_config, hashlib.sha256(
                (ROOT / "config" / "auctionhouse.json").read_bytes()).hexdigest())
            self.assertEqual(before_module, hashlib.sha256(
                (ROOT / "auctions.py").read_bytes()).hexdigest())
        finally:
            temporary.cleanup()

    def test_builder_never_makes_a_directory_itself(self):
        # os.makedirs is named in the docstring only to explain why the module
        # is never imported, so the claim is made over the code.
        code = builder_code()
        self.assertNotIn("makedirs", code)
        self.assertNotIn("os.mkdir", code)
        # The single directory creation is the package's own normalized
        # directory, created for the output it is asked to write.
        creations = re.findall(r"^.*\bmkdir\s*\(.*$", code, re.M)
        self.assertEqual(len(creations), 1, creations)
        self.assertIn("NORMALIZED_DIR", creations[0])


class ImportGraphTests(unittest.TestCase):
    """Design D3: the legacy module is never imported or executed."""

    def test_import_graph_excludes_the_legacy_module(self):
        for line in BUILDER_SOURCE.splitlines():
            match = re.match(r"\s*(import|from)\s+(\S+)", line)
            if not match:
                continue
            module = match.group(2).split(".")[0]
            self.assertNotEqual(module, "auctions", line)
            self.assertNotIn(module, ("get_game_config", "jsonpatch", "flask",
                                      "server", "command", "engine", "bundle",
                                      "requests", "subprocess", "socket",
                                      "urllib", "webbrowser", "http"),
                             "forbidden import: " + line)

    def test_running_the_builder_adds_no_auction_module_to_sys_modules(self):
        temporary, work = make_work_tree()
        self.addCleanup(temporary.cleanup)
        before = set(sys.modules)
        code, _, stderr = run_main(["--repo-root", str(work),
                                    "--out-root", str(work)])
        self.assertEqual(code, 0, stderr)
        added = {name for name in set(sys.modules) - before
                 if name.split(".")[0] == "auctions"}
        self.assertEqual(added, set())

    def test_builder_source_never_executes_the_module(self):
        for forbidden in ("import_module", "__import__", "exec(", "eval(",
                          "compile(", "runpy", "AuctionHouse"):
            self.assertNotIn(forbidden, BUILDER_SOURCE, forbidden)

    def test_legacy_module_is_opened_read_only(self):
        opened = []
        real_io_open = io.open

        def guard(file, mode="r", *args, **kwargs):
            opened.append((str(file), mode))
            return real_io_open(file, mode, *args, **kwargs)

        layers = builder.load_all(str(ROOT))
        self.assertEqual(layers["consumption"]["consumed"], False)
        with mock.patch("io.open", guard):
            layers = builder.load_all(str(ROOT))
        module_path = str((ROOT / "auctions.py").resolve())
        modes = {mode for path, mode in opened if same_file(path, module_path)}
        self.assertTrue(modes)
        for mode in modes:
            self.assertNotIn("w", mode)
            self.assertNotIn("a", mode)
            self.assertNotIn("+", mode)


def same_file(path, other):
    try:
        return str(Path(path).resolve()) == str(Path(other).resolve())
    except OSError:
        return str(path) == str(other)


if __name__ == "__main__":
    unittest.main()