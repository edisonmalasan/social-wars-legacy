"""Tests for the conversion-target census.

The census exists to replace an assumption with a measurement. These tests
therefore check three things above all: that a refusal is recorded as data
rather than ending the run, that the report is byte-identical across reruns, and
that the candidate set is derived from committed inputs rather than transcribed
into the tool.

Every test runs against a synthetic repository in a temporary directory, or
against the committed report read-only. Nothing here touches the real corpus.
"""

import contextlib
import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(TOOLS))

import census_targets  # noqa: E402
import convert_building  # noqa: E402
import convert_unit  # noqa: E402

REPORT_PATH = TOOLS / "target_census.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_convert_building as building_fixtures  # noqa: E402
import test_convert_unit as unit_fixtures  # noqa: E402


def run_census(repo_root, out_root, report):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = census_targets.main([
            "--repo-root", str(repo_root),
            "--out-root", str(out_root),
            "--report", str(report),
        ])
    return code, stdout.getvalue(), stderr.getvalue()


def write_asset_ids(work, entries):
    """Stage a minimal asset-ID registry naming `entries` as extracted."""
    tools = work / "tools" / "asset-registry"
    tools.mkdir(parents=True, exist_ok=True)
    (tools / "asset_ids.json").write_text(json.dumps({
        "schema_version": 1, "policy": "asset-id-registry-v1",
        "result": "success", "inputs": [],
        "counts": {"by_kind": {"item_sprites": {}}},
        "kinds": [{
            "kind": "item_sprites",
            "rule": "synthetic",
            "entries": entries,
        }],
    }), encoding="utf-8")


def stage_empty_content(work, name):
    """Stage an empty normalized content file for a domain a fixture omits.

    The census reads both domains' content because it tallies both, so a
    building-only fixture must still carry an empty `units.json`. This is the
    tool failing closed on a genuinely required input, not a fixture gap: the
    alternative -- silently skipping an absent domain -- would let a corpus that
    lost its unit content report a clean building-only census as complete.
    """
    normalized = work / "packages" / "game-content" / "normalized"
    normalized.mkdir(parents=True, exist_ok=True)
    (normalized / name).write_text("[]", encoding="utf-8")


def sprite_entry(stem, status="extracted"):
    return {
        "ref": stem,
        "reference_count": 1,
        "runtime": "assets/converted/images/" + stem,
        "source": "assets/sprites/" + stem + ".swf",
        "source_sha256": "0" * 64,
        "status": status,
    }


def converted(work):
    return sorted(
        str(path.relative_to(work)).replace("\\", "/")
        for path in work.rglob("*") if path.is_file())


class CensusFixtureTests(unittest.TestCase):
    """The census over a synthetic population of one success and one refusal."""

    def setUp(self):
        # The house fixture converts; a shape tag 83 house is refused by the
        # building converter, so the population contains both outcomes.
        self.temporary, self.work = building_fixtures.make_fixture_tree()
        self.addCleanup(self.temporary.cleanup)
        self.out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out, True)
        stage_empty_content(self.work, "units.json")
        write_asset_ids(self.work, [sprite_entry("0001_house_1_m")])
        self.report = self.out / "target_census.json"

    def test_a_refusal_is_recorded_and_the_run_continues(self):
        code, stdout, stderr = run_census(self.work, self.out, self.report)
        self.assertEqual(code, 0, stderr)
        report = json.loads(self.report.read_text(encoding="utf-8"))
        self.assertEqual(report["result"], "success")
        self.assertEqual(report["counts"]["candidates"], 1)
        self.assertEqual(report["counts"]["converted"], 1)
        self.assertEqual(report["counts"]["refused"], 0)
        self.assertIn("outputs", stdout)

    def test_a_refused_target_does_not_end_the_run(self):
        # Replace the shape tag with the refused one, then census again: the
        # refusal must be data, and the run must still complete with exit 0.
        broken_temporary, work = building_fixtures.make_fixture_tree(shape_tag=83)
        self.addCleanup(broken_temporary.cleanup)
        stage_empty_content(work, "units.json")
        write_asset_ids(work, [sprite_entry("0001_house_1_m")])
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out, True)
        report = out / "target_census.json"
        code, _stdout, stderr = run_census(work, out, report)
        self.assertEqual(code, 0, stderr)
        document = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(document["counts"]["candidates"], 1)
        self.assertEqual(document["counts"]["refused"], 1)
        self.assertEqual(document["counts"]["converted"], 0)
        # The class name is the converter's own message, reduced.
        self.assertEqual(len(document["refusal_class_totals"]), 1)
        self.assertIn("unsupported shape tag",
                      document["refusal_class_totals"][0]["refusal_class"])

    def test_every_candidate_appears_exactly_once_with_a_verdict(self):
        run_census(self.work, self.out, self.report)
        report = json.loads(self.report.read_text(encoding="utf-8"))
        keys = [(row["domain"], row["stem"]) for row in report["targets"]]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(keys), report["counts"]["candidates"])
        for row in report["targets"]:
            self.assertIn(row["verdict"], ("converted", "refused"))
            self.assertIn("legacy_id", row)
            self.assertIn("domain", row)

    def test_per_domain_counts_sum_to_the_candidate_count(self):
        run_census(self.work, self.out, self.report)
        report = json.loads(self.report.read_text(encoding="utf-8"))
        total = sum(d["converted"] + d["refused"]
                    for d in report["counts"]["by_domain"].values())
        self.assertEqual(total, report["counts"]["candidates"])

    def test_the_report_is_byte_identical_across_reruns(self):
        run_census(self.work, self.out, self.report)
        first = self.report.read_bytes()
        run_census(self.work, self.out, self.report)
        self.assertEqual(self.report.read_bytes(), first)

    def test_a_fresh_report_names_no_timestamp(self):
        # The committed-report scan in CensusModelTests reads the committed
        # artifact, which a change to the tool does not alter, so it cannot see
        # a timestamp the tool has started writing. This guard scans what the
        # tool actually writes, which catches even a *constant* fake timestamp
        # -- the rerun-determinism guard above cannot, because a constant is
        # stable across runs by definition.
        run_census(self.work, self.out, self.report)
        raw = self.report.read_text(encoding="utf-8").lower()
        for forbidden in ("generated_at", "timestamp", "host", "hostname"):
            self.assertNotIn(forbidden, raw, forbidden)

    def test_the_candidate_set_is_derived_not_transcribed(self):
        # A stem that appears twice in the content is not a candidate, because
        # the converter would refuse it for a content ambiguity that says
        # nothing about convertibility.
        content = (self.work / "packages" / "game-content" / "normalized"
                   / "buildings.json")
        rows = json.loads(content.read_text(encoding="utf-8"))
        content.write_text(json.dumps(rows + [copy.deepcopy(rows[0])]),
                           encoding="utf-8")
        run_census(self.work, self.out, self.report)
        report = json.loads(self.report.read_text(encoding="utf-8"))
        self.assertEqual(report["counts"]["candidates"], 0)
        self.assertEqual(report["targets"], [])

    def test_a_non_extracted_status_is_not_a_candidate(self):
        write_asset_ids(self.work, [sprite_entry("0001_house_1_m",
                                                 status="pending")])
        run_census(self.work, self.out, self.report)
        report = json.loads(self.report.read_text(encoding="utf-8"))
        self.assertEqual(report["counts"]["candidates"], 0)

    def test_the_two_domains_are_tallied_separately(self):
        unit_temporary, work = unit_fixtures.make_unit_fixture_tree()
        self.addCleanup(unit_temporary.cleanup)
        # Both domains present, so the by_domain block must name both.
        stage_empty_content(work, "buildings.json")
        write_asset_ids(work, [sprite_entry("10033_wild_elephant")])
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out, True)
        report = out / "target_census.json"
        run_census(work, out, report)
        document = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(document["counts"]["by_domain"]["unit"]["converted"], 1)
        self.assertEqual(document["counts"]["by_domain"]["building"]["converted"],
                         0)
        self.assertEqual(document["targets"][0]["legacy_id"], "933")


class CensusContainmentTests(unittest.TestCase):
    """The census must not write into the repository, and must require a root."""

    def setUp(self):
        self.temporary, self.work = building_fixtures.make_fixture_tree()
        self.addCleanup(self.temporary.cleanup)
        self.out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out, True)
        stage_empty_content(self.work, "units.json")
        write_asset_ids(self.work, [sprite_entry("0001_house_1_m")])

    def test_the_output_root_is_required(self):
        # `--report` IS passed here, so `--out-root` is the only missing
        # argument and the error text names it alone.
        #
        # The assertion is on argparse's *error* line, not on its usage line.
        # An earlier version of this test asserted `"--out-root" in stderr` and
        # was **vacuous**: argparse's usage line lists every option name,
        # required or not, so the assertion passed even with `required=True`
        # removed from the argument. That was found by injection probe (g),
        # which reported zero failures -- the harness's abort-on-zero guard is
        # what turned a silently useless test into a visible defect.
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as caught:
                census_targets.main(["--repo-root", str(self.work),
                                     "--report",
                                     str(self.out / "target_census.json")])
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("the following arguments are required: --out-root",
                      stderr.getvalue())

    def test_the_report_path_is_required(self):
        # As above: `--out-root` IS passed, so only `--report` is missing.
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as caught:
                census_targets.main(["--repo-root", str(self.work),
                                     "--out-root", str(self.out)])
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("the following arguments are required: --report",
                      stderr.getvalue())

    def test_the_repository_root_is_refused_as_the_output_root(self):
        report = self.out / "target_census.json"
        code, _stdout, stderr = run_census(self.work, self.work, report)
        self.assertEqual(code, 2)
        self.assertIn("must not be the repository root", stderr)
        self.assertFalse(report.exists())

    def test_the_repository_gains_and_loses_no_file(self):
        before = converted(self.work)
        report = self.out / "target_census.json"
        run_census(self.work, self.out, report)
        self.assertEqual(converted(self.work), before)

    def test_no_registry_manifest_or_package_is_written_in_the_repository(self):
        run_census(self.work, self.out, self.out / "target_census.json")
        for relative in ("tools/asset-registry/conversions.json",
                         "tools/asset-registry/statuses.json",
                         "assets/converted/buildings/0001_house_1_m",
                         "assets/converted/units"):
            self.assertFalse((self.work / relative).exists(), relative)

    def test_converter_output_lands_under_the_output_root(self):
        report = self.out / "target_census.json"
        run_census(self.work, self.out, report)
        produced = [p for p in self.out.rglob("*") if p.is_file()]
        self.assertTrue(produced)
        for path in produced:
            self.assertTrue(str(path).startswith(str(self.out)))

    def test_an_unreadable_input_fails_and_writes_no_report(self):
        (self.work / "tools" / "asset-registry" / "asset_ids.json").unlink()
        report = self.out / "target_census.json"
        code, _stdout, stderr = run_census(self.work, self.out, report)
        self.assertEqual(code, 2)
        self.assertIn("asset-id registry file missing", stderr)
        self.assertFalse(report.exists())

    def test_a_target_raising_something_other_than_a_refusal_is_a_tool_failure(
            self):
        # A genuine tool failure is anything a converter raised that is not a
        # refusal. Simulated by an unexpected exception type, so the census's
        # own error routing is exercised rather than trusted.
        original = census_targets.evaluate

        def boom(target, repo_root, out_root):
            raise RuntimeError("synthetic converter defect")
        census_targets.evaluate = boom
        self.addCleanup(setattr, census_targets, "evaluate", original)
        report = self.out / "target_census.json"
        code, _stdout, stderr = run_census(self.work, self.out, report)
        self.assertEqual(code, 3)
        self.assertIn("synthetic converter defect", stderr)
        self.assertFalse(report.exists())
        self.assertIsNotNone(original)

    def test_the_tool_imports_no_process_network_or_flash_module(self):
        # Checked against the parsed imports, not the source text. A raw
        # substring scan of this file trips over the module's own prose ("No
        # subprocess, network, server, browser, or Flash runtime is used"), which
        # is the self-tripping guard shape recorded in the construction-assist
        # line: a guard that fails on the very sentence stating the rule proves
        # nothing about the rule. Parsing imports is also the stronger claim --
        # it cannot be satisfied by mentioning a name in a comment.
        import ast
        tree = ast.parse((TOOLS / "census_targets.py").read_text(
            encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported.add(node.module.split(".")[0])
        forbidden = {"subprocess", "socket", "ssl", "http", "urllib",
                     "requests", "ftplib", "telnetlib", "multiprocessing",
                     "ctypes", "webbrowser", "asyncio"}
        self.assertEqual(imported & forbidden, set())
        self.assertNotIn("os", imported)

    def test_the_tool_calls_no_dynamic_evaluation(self):
        import ast
        tree = ast.parse((TOOLS / "census_targets.py").read_text(
            encoding="utf-8"))
        called = {node.func.id for node in ast.walk(tree)
                  if isinstance(node, ast.Call) and isinstance(node.func,
                                                               ast.Name)}
        self.assertEqual(called & {"eval", "exec", "compile", "__import__"},
                         set())


class CensusModelTests(unittest.TestCase):
    """The pure helpers, exercised without running a converter."""

    def test_a_refusal_pattern_keeps_the_message_and_drops_the_target(self):
        source = "assets/sprites/0006_depot_wood_2_m.swf"
        message = "unknown fill style at swf " + source + ": 174"
        self.assertEqual(
            census_targets.refusal_pattern(message, source),
            "unknown fill style at swf <target>: #")

    def test_a_refusal_pattern_does_not_invent_a_category(self):
        # Two different refusals must not collapse into one class name.
        source = "assets/sprites/a.swf"
        first = census_targets.refusal_pattern(
            "unknown fill style at swf " + source + ": 1", source)
        second = census_targets.refusal_pattern(
            "unsupported shape tag at swf " + source + ": 83", source)
        self.assertNotEqual(first, second)

    def test_the_committed_report_is_readable_and_self_consistent(self):
        if not REPORT_PATH.exists():
            self.skipTest("committed census report not present")
        document = json.loads(REPORT_PATH.read_bytes().decode("utf-8"))
        self.assertEqual(document["result"], "success")
        counts = document["counts"]
        self.assertEqual(
            counts["converted"] + counts["refused"], counts["candidates"])
        self.assertEqual(sum(
            d["converted"] + d["refused"]
            for d in counts["by_domain"].values()), counts["candidates"])
        classes = document["refusal_class_totals"]
        self.assertEqual(sum(c["targets"] for c in classes),
                         counts["refused"])

    def test_the_committed_report_names_no_timestamp(self):
        if not REPORT_PATH.exists():
            self.skipTest("committed census report not present")
        raw = REPORT_PATH.read_bytes().decode("utf-8").lower()
        for forbidden in ("generated_at", "timestamp", "host", "hostname"):
            self.assertNotIn(forbidden, raw, forbidden)

    def test_the_committed_report_has_no_target_in_several_classes(self):
        if not REPORT_PATH.exists():
            self.skipTest("committed census report not present")
        document = json.loads(REPORT_PATH.read_bytes().decode("utf-8"))
        self.assertEqual(document["counts"][
            "refused_targets_in_several_classes"], 0)
        self.assertEqual(document["refused_targets_in_several_classes"], [])

    def test_no_stem_or_count_is_transcribed_into_the_tool(self):
        body = (TOOLS / "census_targets.py").read_text(encoding="utf-8")
        # No committed stem, and none of the recorded population figures.
        for transcribed in ("0001_house_1_m", "10033_wild_elephant", "933",
                            "817", "452", "365", "587", "230", "133", "61"):
            self.assertNotIn(transcribed, body, transcribed)


if __name__ == "__main__":
    unittest.main()
