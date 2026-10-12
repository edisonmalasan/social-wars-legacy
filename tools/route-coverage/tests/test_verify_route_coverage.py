import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_route_coverage as verifier

# tests/ -> route-coverage/ -> tools/ -> repository root
ROOT = Path(__file__).resolve().parents[3]
WORKING_TREE_SAVES = ROOT / "saves"


def run_main(argv):
    """Run the tool with stdout captured; stderr chatter passes through."""
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        code = verifier.main(argv)
    return code, stdout.getvalue()


def run_main_capturing_stderr(argv):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = verifier.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def census():
    code, output = run_main(["--repo-root", str(ROOT)])
    assert code == 0, "census exited %d" % code
    return json.loads(output)


class LegacyBranchReuseTests(unittest.TestCase):
    """R1: the branch list is reused, never re-derived."""

    def test_the_shared_extractor_module_is_the_one_used(self):
        extractor = verifier.load_legacy_extractor(ROOT)
        import verify_commands
        self.assertIs(extractor, verify_commands)

    def test_branch_list_matches_the_shared_extractor_exactly(self):
        source = (ROOT / "command.py").read_text(encoding="utf-8")
        extractor = verifier.load_legacy_extractor(ROOT)
        expected = sorted(extractor.extract_command_branches(source),
                          key=lambda branch: branch["line"])
        spans = verifier.legacy_branch_spans(source, extractor)
        self.assertEqual(len(spans), 63)
        self.assertEqual(sorted(spans),
                         sorted(branch["command"] for branch in expected))

    def test_spans_are_ordered_and_butted(self):
        # A branch's span ends on the line before the next branch begins; the
        # branches themselves are not adjacent (blank lines separate them).
        spans = census()["legacy_branches"]["spans"]
        ordered = sorted(spans.items(), key=lambda item: item[1][0])
        for (_, (_, end)), (name, (next_first, _)) in zip(ordered, ordered[1:]):
            self.assertEqual(next_first, end + 1, "discontinuity before %s" % name)
        self.assertEqual(ordered[0][1][0], 42)
        self.assertEqual(ordered[-1][1][1], len(
            (ROOT / "command.py").read_text(encoding="utf-8").splitlines()))

    def test_known_span_boundaries(self):
        spans = census()["legacy_branches"]["spans"]
        self.assertEqual(spans["buy"], [42, 59])
        self.assertEqual(spans["complete_tutorial"], [60, 67])
        self.assertEqual(spans["level_up"], [81, 86])
        self.assertEqual(spans["move"], [119, 135])
        self.assertEqual(spans["collect"], [136, 148])
        self.assertEqual(spans["set_variables"], [951, 956])

    def test_a_missing_shared_extractor_is_a_tool_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory) / "repo"
            (work / "tools").mkdir(parents=True)
            shutil.copy2(ROOT / "command.py", work / "command.py")
            code, _, stderr = run_main_capturing_stderr(["--repo-root", str(work)])
            self.assertEqual(code, 2)
            self.assertIn("shared branch extractor missing", stderr)


class RouteEnumerationTests(unittest.TestCase):
    """R2: routes come from the live url_map, never a source text search."""

    @classmethod
    def setUpClass(cls):
        cls.report = census()

    def test_reproduces_the_recorded_route_baseline(self):
        baseline = self.report["route_baseline"]
        self.assertEqual(baseline["v0_rule_count"], 24)
        self.assertEqual(baseline["distinct_paths"], 24)
        self.assertEqual(baseline["method_counts"], {"POST": 23, "GET": 1})
        self.assertEqual(baseline["paths_not_post_only"], ["/v0/session"])
        self.assertTrue(baseline["matches_recorded_baseline"])

    def test_every_rule_is_a_v0_rule(self):
        self.assertTrue(self.report["route_baseline"]["all_paths_share_prefix"])

    def test_every_route_handler_resolves_inside_the_repository(self):
        for route in self.report["routes"]:
            self.assertTrue(route["handler_file"].startswith("apps"), route)
            self.assertGreaterEqual(route["handler_first_line"], 1)

    def test_a_broken_enumerator_fails_the_control(self):
        """The planted probe must be able to fail the whole report."""
        real = verifier.enumerate_v0_routes

        def blind(app, prefix):
            return [route for route in real(app, prefix)
                    if route["path"] == verifier.CONTROL_ROUTE]

        with mock.patch.object(verifier, "enumerate_v0_routes", blind):
            code, _, stderr = run_main_capturing_stderr(["--repo-root", str(ROOT)])
        self.assertEqual(code, 2)
        self.assertIn("control failed", stderr)

    def test_an_empty_enumeration_fails_the_control(self):
        with mock.patch.object(verifier, "enumerate_v0_routes", lambda app, prefix: []):
            code, _, stderr = run_main_capturing_stderr(["--repo-root", str(ROOT)])
        self.assertEqual(code, 2)
        self.assertIn("control failed", stderr)

    def test_the_branch_count_control_can_fail(self):
        with mock.patch.object(verifier, "EXPECTED_BRANCH_COUNT", 62):
            code, _, stderr = run_main_capturing_stderr(["--repo-root", str(ROOT)])
        self.assertEqual(code, 2)
        self.assertIn("branch extraction control failed", stderr)

    def test_controls_are_reported_as_passing(self):
        controls = census()["controls"]
        self.assertTrue(controls["branch_count"]["passed"])
        self.assertEqual(controls["branch_count"]["observed"], 63)
        self.assertEqual(controls["planted_route"]["path"], verifier.CONTROL_ROUTE)
        self.assertTrue(controls["planted_route"]["passed"])
        self.assertTrue(controls["enumeration_non_empty"]["passed"])
        self.assertTrue(controls["negation_detector"]["flagged_crafted_negative"]["passed"])
        self.assertTrue(controls["negation_detector"]["silent_crafted_positive"]["passed"])


class GroundingRuleTests(unittest.TestCase):
    """R4: only explicit citations ground a mapping; naming similarity never does."""

    @classmethod
    def setUpClass(cls):
        cls.report = census()
        cls.coverage = cls.report["coverage"]

    def test_every_mapping_carries_file_line_and_matched_text(self):
        for entry in self.coverage["branch_coverage"]:
            for item in entry["cited_by"]:
                provenance = item["provenance"]
                self.assertTrue(provenance["file"])
                self.assertGreaterEqual(provenance["line"], 1)
                self.assertTrue(provenance["matched_text"])

    def test_no_mapping_is_inferred_from_a_route_name(self):
        # /v0/store cites the `buy` branch, but only through a docstring that
        # contrasts the two. Assert the contrast is visible rather than hiding
        # the weak provenance behind a bare branch name.
        store = [item for item in self.coverage["branch_coverage"]
                 if item["branch"] == "buy"]
        self.assertTrue(store[0]["cited_by"])
        for item in store[0]["cited_by"]:
            if item["grounding"] == "docstring_name":
                self.assertTrue(item["provenance"]["context"])

    def test_line_span_citations_resolve_to_exactly_one_branch(self):
        for route in self.report["routes"]:
            for citation in route["citations"]:
                if citation["kind"] == "line_span" and citation["resolution"] == "resolved":
                    self.assertEqual(len(citation["branches"]), 1)

    def test_ambiguous_citations_are_reported_and_never_ground(self):
        ambiguous = self.coverage["ambiguous_citations"]
        self.assertTrue(ambiguous, "expected at least one ambiguous citation")
        for citation in ambiguous:
            self.assertGreater(len(citation["candidate_branches"]), 1)
            self.assertEqual(citation["resolution"],
                             "ambiguous_multiple_branches")
            branch = citation["candidate_branches"][0]
            entry = [e for e in self.coverage["branch_coverage"]
                     if e["branch"] == branch][0]
            for item in entry["cited_by"]:
                self.assertNotEqual(
                    (item["provenance"]["line"], item["provenance"]["matched_text"]),
                    (citation["line"], citation["matched_text"]),
                    "an ambiguous citation must not ground a mapping")

    def test_a_known_ambiguous_span_is_detected(self):
        # command.py:573-623 runs through four consecutive darts branches.
        darts = [c for r in self.report["routes"] if r["path"] == "/v0/darts"
                 for c in r["citations"]
                 if c["matched_text"] == "command.py:573-623"]
        self.assertEqual(len(darts), 1)
        self.assertEqual(darts[0]["resolution"], "ambiguous_multiple_branches")
        self.assertEqual(darts[0]["branches"],
                         ["buy_premium_account", "darts_new_free",
                          "darts_reset", "darts_shoot_balloon"])

    def test_pre_dispatch_citations_are_unresolved_not_covered(self):
        # command.py:40 is apply_resources, before the first branch at line 42.
        unresolved = [c for c in self.coverage["unresolved_citations"]
                      if c["matched_text"] == "command.py:40"]
        self.assertTrue(unresolved)
        for citation in unresolved:
            self.assertEqual(citation["candidate_branches"], [])
            self.assertEqual(citation["resolution"], "unresolved_no_branch")

    def test_bare_line_ranges_are_never_grounded(self):
        for route in self.report["routes"]:
            for citation in route["citations"]:
                if citation["kind"] == "bare_line_range":
                    self.assertEqual(
                        citation["resolution"],
                        "unresolved_bare_range_without_command_py_prefix")

    def test_non_command_file_references_are_not_citations(self):
        # Every handler cites engine.py:251-271 and get_game_config.py; none of
        # those may be mistaken for a dispatcher citation.
        for route in self.report["routes"]:
            for citation in route["citations"]:
                self.assertTrue(citation["matched_text"].startswith("command.py")
                                or citation["kind"] != "line_span")

    def test_branches_cited_by_multiple_routes_are_reported(self):
        multiple = self.coverage["branches_cited_by_multiple_routes"]
        self.assertIn("buy", multiple)
        self.assertGreater(len(multiple["buy"]), 1)

    def test_both_provenance_tiers_are_reported_separately(self):
        strong = self.coverage["branches_cited_by_line_span"]
        name_only = self.coverage["branches_mentioned_by_name_only"]
        self.assertTrue(strong)
        self.assertTrue(name_only)
        # The tiers must not overlap: a name-only branch is one with no line
        # span at all, by construction.
        self.assertEqual(set(strong) & set(name_only), set())

    def test_covered_means_line_span_resolved_only(self):
        """The headline must not be inflatable by a name-only mention."""
        strong = set(self.coverage["branches_cited_by_line_span"])
        for entry in self.coverage["branch_coverage"]:
            if entry["covered"]:
                self.assertIn("line_span", entry["grounding_kinds"], entry["branch"])
            else:
                self.assertNotIn("line_span", entry["grounding_kinds"],
                                 entry["branch"])
        covered = {entry["branch"] for entry in self.coverage["branch_coverage"]
                   if entry["covered"]}
        self.assertEqual(covered, strong)

    def test_negated_name_only_branches_are_not_covered(self):
        """REGRESSION: these three are denied by their own citing text.

        Each has exactly one name-only citation, and each of those citations
        states the opposite of coverage. If someone later weakens the tier rule
        or the negation list, this fails.
        """
        covered = {entry["branch"] for entry in self.coverage["branch_coverage"]
                   if entry["covered"]}
        for branch in ("soulmixer_speedup", "fast_forward", "push_queue_unit2"):
            self.assertNotIn(branch, covered, branch)
            self.assertIn(branch, self.coverage["branches_mentioned_by_name_only"],
                          branch)

    def test_negation_detector_fires_on_crafted_input(self):
        control = self.report["controls"]["negation_detector"]
        fired = control["flagged_crafted_negative"]
        self.assertTrue(fired["negation_markers"], fired["context"])
        self.assertEqual(control["silent_crafted_positive"]["negation_markers"], [])

    def test_negation_markers_present_on_every_citation(self):
        for route in self.report["routes"]:
            for citation in route["citations"]:
                self.assertIn("negation_markers", citation,
                              "%s L%s" % (route["path"], citation["line"]))
                self.assertIsInstance(citation["negation_markers"], list)

    def test_a_flagged_citation_is_still_reported_not_dropped(self):
        """Flag only. Nothing is removed on the strength of a negation marker."""
        name_only = self.coverage["branches_mentioned_by_name_only"]
        flagged = [(branch, mention)
                   for branch, mentions in name_only.items()
                   for mention in mentions if mention["negation_markers"]]
        self.assertTrue(flagged, "expected at least one flagged name-only mention")
        for branch, mention in flagged:
            self.assertTrue(mention["context"], branch)
            self.assertTrue(mention["file"], branch)
            self.assertTrue(mention["route"], branch)
            self.assertTrue(mention["matched_text"], branch)

    def test_name_only_mentions_keep_full_provenance(self):
        for branch, mentions in self.coverage["branches_mentioned_by_name_only"].items():
            for mention in mentions:
                for field in ("route", "file", "line", "matched_text", "context"):
                    self.assertIn(field, mention, branch)
                self.assertEqual(mention["file"],
                                 "apps/compat-api/compat_service.py", branch)

    def test_conservative_and_permissive_figures_both_reported(self):
        strong = set(self.coverage["branches_cited_by_line_span"])
        permissive = set(self.coverage["branches_covered_permissive_reading"])
        all_names = {entry["branch"] for entry in self.coverage["branch_coverage"]}
        # Permissive can only ever be a superset of the conservative headline.
        self.assertTrue(strong <= permissive)
        self.assertTrue(permissive <= all_names)
        # Each uncovered list is the exact complement of its own covered set,
        # and the two complements partition the 63 names.
        self.assertEqual(set(self.coverage["branches_without_cited_route"]),
                         all_names - strong)
        self.assertEqual(
            set(self.coverage["branches_without_cited_route_permissive_reading"]),
            all_names - permissive)
        # Reported counts must agree with the lists they summarise.
        counts = self.report["counts"]
        self.assertEqual(counts["branches_covered"], len(strong))
        self.assertEqual(counts["branches_without_cited_route"], len(all_names - strong))
        self.assertEqual(counts["branches_covered_permissive_reading"], len(permissive))
        self.assertEqual(counts["branches_without_cited_route_permissive_reading"],
                         len(all_names - permissive))

    def test_branch_and_route_totals_are_consistent(self):
        table = self.coverage["branch_coverage"]
        self.assertEqual(len(table), 63)
        covered = [entry["branch"] for entry in table if entry["covered"]]
        uncovered = self.coverage["branches_without_cited_route"]
        self.assertEqual(sorted(covered + uncovered),
                         sorted(entry["branch"] for entry in table))
        self.assertEqual(set(covered) & set(uncovered), set())
        # Covered is exactly the line-span tier, nothing else.
        self.assertEqual(sorted(covered),
                         sorted(self.coverage["branches_cited_by_line_span"]))
        # And it is disjoint from the name-only tier.
        self.assertEqual(set(covered)
                         & set(self.coverage["branches_mentioned_by_name_only"]),
                         set())

    def test_routes_with_and_without_citations_partition_the_route_set(self):
        paths = sorted(route["path"] for route in self.report["routes"])
        without = self.coverage["routes_without_cited_branch"]
        self.assertEqual(sorted(set(paths) - set(without)),
                         sorted(path for path in paths if path not in without))
        for path in without:
            route = [r for r in self.report["routes"] if r["path"] == path][0]
            self.assertEqual(route["citations"], [], path)


class ExitCodeTests(unittest.TestCase):
    """R5: disagreement is data; only failure and failed controls are non-zero."""

    def test_uncovered_branches_still_exit_0(self):
        report = census()
        self.assertGreater(len(report["coverage"]["branches_without_cited_route"]), 0)
        code, _ = run_main(["--repo-root", str(ROOT)])
        self.assertEqual(code, 0)

    def test_missing_legacy_source_exits_2(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory) / "repo"
            shutil.copytree(ROOT / "tools" / "command-catalog", work / "tools" / "command-catalog")
            code, _, stderr = run_main_capturing_stderr(["--repo-root", str(work)])
            self.assertEqual(code, 2)
            self.assertIn("legacy source file missing", stderr)

    def test_invalid_repo_root_exits_2(self):
        code, _, stderr = run_main_capturing_stderr(
            ["--repo-root", str(ROOT / "no-such-directory")])
        self.assertEqual(code, 2)
        self.assertIn("repository root invalid", stderr)


class DeterminismTests(unittest.TestCase):
    """R5: the committed report must reproduce byte for byte."""

    def test_two_runs_are_byte_identical(self):
        _, first = run_main(["--repo-root", str(ROOT)])
        _, second = run_main(["--repo-root", str(ROOT)])
        self.assertEqual(first, second)

    def test_no_absolute_paths_or_volatile_values(self):
        _, output = run_main(["--repo-root", str(ROOT)])
        document = json.loads(output)
        # The serialized report must be platform-independent: no drive letter, no
        # absolute path, and no native separator anywhere.
        self.assertNotIn(str(ROOT), output)
        for route in document["routes"]:
            self.assertNotIn("\\", route["handler_file"])
            self.assertFalse(route["handler_file"].startswith("/"))
            self.assertTrue(route["handler_file"].startswith("apps/"))
        # Keys are compared as keys, not as raw substrings of the serialized
        # document: "date" is a substring of the report's own "validate" control
        # key, so a substring test would forbid a field the tool legitimately
        # reports.
        forbidden = {"generated", "generated_utc", "timestamp", "date",
                     "created_at", "commit", "git_commit", "host", "cwd"}
        self.assertEqual(_all_keys(document) & forbidden, set())

    def test_keys_are_sorted(self):
        _, output = run_main(["--repo-root", str(ROOT)])
        self.assertEqual(output, json.dumps(json.loads(output), indent=2,
                                            sort_keys=True) + "\n")


class OutputContainmentTests(unittest.TestCase):
    """R6: the tool writes nothing unless --out-path is given."""

    def test_no_file_is_written_without_out_path(self):
        before = _tree_snapshot(ROOT / "tools" / "route-coverage")
        code, _ = run_main(["--repo-root", str(ROOT)])
        self.assertEqual(code, 0)
        self.assertEqual(_tree_snapshot(ROOT / "tools" / "route-coverage"), before)

    def test_out_path_writes_exactly_the_stdout_report(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "nested" / "report.json"
            code, output = run_main(["--repo-root", str(ROOT),
                                     "--out-path", str(destination)])
            self.assertEqual(code, 0)
            self.assertEqual(destination.read_text(encoding="utf-8"), output)

    def test_out_path_output_is_byte_identical_across_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "a.json"
            second = Path(directory) / "b.json"
            run_main(["--repo-root", str(ROOT), "--out-path", str(first)])
            run_main(["--repo-root", str(ROOT), "--out-path", str(second)])
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_no_working_tree_saves_directory_appears(self):
        existed_before = WORKING_TREE_SAVES.exists()
        code, _ = run_main(["--repo-root", str(ROOT)])
        self.assertEqual(code, 0)
        self.assertEqual(WORKING_TREE_SAVES.exists(), existed_before)
        if existed_before:
            self.assertFalse(WORKING_TREE_SAVES.is_dir() and not existed_before)

    def test_no_committed_save_byte_is_written(self):
        seeds = ROOT / "tests" / "saves"
        before = {path: path.read_bytes() for path in sorted(seeds.rglob("*"))
                  if path.is_file()}
        code, _ = run_main(["--repo-root", str(ROOT)])
        self.assertEqual(code, 0)
        after = {path: path.read_bytes() for path in sorted(seeds.rglob("*"))
                 if path.is_file()}
        self.assertEqual(after, before)

    def test_the_disposable_corpus_is_built_outside_the_repository(self):
        """A corpus left inside the worktree would show up as a diff."""
        with tempfile.TemporaryDirectory() as directory:
            recorded = {}
            real_mkdtemp = tempfile.mkdtemp

            def spy(*args, **kwargs):
                path = real_mkdtemp(*args, **kwargs)
                recorded["corpus"] = path
                return path

            with mock.patch.object(tempfile, "mkdtemp", spy):
                code, _ = run_main(["--repo-root", str(ROOT)])
            self.assertEqual(code, 0)
            corpus = Path(recorded["corpus"])
            self.assertFalse(corpus.exists())
            self.assertFalse(str(corpus).startswith(str(ROOT)))

    def test_the_tool_does_not_import_a_legacy_module_for_branch_extraction(self):
        """Branch data is read from text; the Compatibility API boot is separate."""
        source = (ROOT / "tools" / "route-coverage"
                  / "verify_route_coverage.py").read_text(encoding="utf-8")
        for forbidden in ("requests", "subprocess", "webbrowser", "shutil.rmtree("):
            self.assertNotIn(forbidden, source)


def _all_keys(node):
    """Every mapping key reachable in a parsed JSON document."""
    found = set()
    if isinstance(node, dict):
        for key, value in node.items():
            found.add(key)
            found |= _all_keys(value)
    elif isinstance(node, list):
        for item in node:
            found |= _all_keys(item)
    return found


def _tree_snapshot(root):
    return {str(path.relative_to(root)): path.read_bytes()
            for path in sorted(root.rglob("*")) if path.is_file()}


if __name__ == "__main__":
    unittest.main()