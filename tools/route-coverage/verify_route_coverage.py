"""Offline legacy-branch / modern-route coverage census.

Measures how many of the preserved legacy dispatcher's named command branches
are cited by a modern Compatibility API route. Two inputs:

* the legacy branch list, REUSED from ``tools/command-catalog/`` rather than
  re-derived here (see ``LEGACY_EXTRACTOR_SOURCE``);
* the modern route list, read from the LIVE Flask ``url_map`` -- never from a
  text search over the service source, because a previous measurement of this
  same question matched a docstring that merely quoted a decorator.

A route/branch mapping is reported ONLY when the route handler's own source
cites that branch explicitly, by a ``command.py:NNN`` line span resolving inside
the branch's span, or by the branch's name appearing in backticks in the
handler's docstring. A route name that *looks* related to a branch name is not
evidence; nothing is inferred from naming.

"Covered" is the STRONG tier only: a resolved ``command.py:NNN`` line span.
A backticked branch name is evidence the handler CITES the branch, not that it
implements it -- several handlers name a branch precisely to contrast
themselves with it. Name-only mentions are therefore reported in full, with
their verbatim citing line and a negation flag, and never counted as covered.

The census is a scoping instrument, not a game rule. An uncovered branch is
DATA, not an error: exit 0 unless the tool itself failed or a control failed.
Python 3.9, standard library only (plus the repository's own Flask, which is
already a pinned dependency of the Compatibility API this tool must import).
"""

import argparse
import contextlib
import inspect
import json
import os
from pathlib import Path
import re
import sys

LEGACY_SOURCE_FILE = "command.py"
LEGACY_EXTRACTOR_SOURCE = "tools/command-catalog/verify_commands.py"
SERVICE_RELATIVE = Path("apps") / "compat-api"
CONTROL_ROUTE = "/v0/__control_probe__"
CONTROL_ENDPOINT = "route_coverage_control_probe"
CONTROL_VIEW = "route_coverage_control_probe_view"
EXPECTED_BRANCH_COUNT = 63
ROUTE_PREFIX = "/v0"
MAX_SOURCE_BYTES = 4 * 1024 * 1024
DOCSTRING_QUOTES = ('"""', "'''")

#: ``command.py:NNN`` and ``command.py:NNN-MMM`` citations. Anchored on the file
#: name so an ``engine.py:NNN`` or ``get_game_config.py:NNN`` reference in the
#: same docstring cannot be mistaken for a dispatcher citation.
CITATION_PATTERN = re.compile(r"command\.py:(\d+)(?:-(\d+))?")

#: A backticked span with no ``command.py:`` prefix, e.g. ``76-79``. These are
#: reported as unresolved rather than grounded: R4 admits a ``command.py:NNN``
#: span or a branch name, and nothing else.
BARE_SPAN_PATTERN = re.compile(r"^\d+-\d+$")

BACKTICK_PATTERN = re.compile(r"`([^`\n]+)`")

#: Substrings that mark a citation's own sentence as DENYING the branch it
#: names. Scanned case-insensitively against the verbatim citing line.
#:
#: This list is a FLAG, never a filter. A flagged citation still appears in the
#: report with ``negation_markers`` populated, because deciding whether a
#: sentence negates or merely qualifies is a judgement for a reader, not for a
#: regex. The list is deliberately short and explicit rather than clever: every
#: entry is a word a documentation author would use to say "this route does not
#: do that".
NEGATION_MARKERS = (
    "no ",
    "not ",
    "never",
    "ignored",
    "unlike",
    "without",
    "no-op",
    "none of",
)

#: A crafted context used ONLY to prove the negation detector can fire. If this
#: input ever fails to be flagged, the detector is inert and every
#: ``negation_markers`` list in the report is worthless, so the control refuses
#: to report rather than emitting confident empty lists.
NEGATION_CONTROL_POSITIVE = (
    "``soulmixer_speedup`` has no action here at all: the legacy branch needs"
)
NEGATION_CONTROL_NEGATIVE = (
    "``activate`` writes the click counter recorded by the legacy branch"
)


class VerificationError(Exception):
    """Genuine tool failure: bad input, unsupported syntax, or a failed control."""


def read_text_file(path, role):
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        raise VerificationError(role + " file missing: " + str(path))
    except OSError:
        raise VerificationError(role + " file unreadable: " + str(path))
    if len(data) > MAX_SOURCE_BYTES:
        raise VerificationError(role + " file too large: " + str(path))
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise VerificationError(role + " file not utf-8: " + str(path))


# --------------------------------------------------------------- legacy side --
def load_legacy_extractor(repo_root):
    """Import the command-catalog branch extractor instead of re-deriving it."""
    path = repo_root / LEGACY_EXTRACTOR_SOURCE
    if not path.is_file():
        raise VerificationError("shared branch extractor missing: " + LEGACY_EXTRACTOR_SOURCE)
    sys.path.insert(0, str(path.parent))
    try:
        import verify_commands as extractor
    except ImportError as error:
        raise VerificationError("shared branch extractor not importable: %s" % (error,))
    for required in ("extract_command_branches", "_literal_command_name"):
        if not hasattr(extractor, required):
            raise VerificationError("shared branch extractor lacks " + required)
    return extractor


def legacy_branch_spans(source_text, extractor):
    """Return ``{branch: (first_line, last_line)}`` for the dispatcher.

    Each branch runs from its own ``if``/``elif`` line to the line before the
    next branch's; the last branch runs to the end of ``do_command``. The span
    is a derived convenience for resolving line citations, and it is reported
    in the output so a reader can check it rather than trust it.
    """
    branches = sorted(extractor.extract_command_branches(source_text),
                      key=lambda branch: branch["line"])
    if not branches:
        raise VerificationError("legacy dispatcher resolved zero branches")
    last_line = len(source_text.splitlines())
    spans = {}
    for index, branch in enumerate(branches):
        end = branches[index + 1]["line"] - 1 if index + 1 < len(branches) else last_line
        if end < branch["line"]:
            raise VerificationError("legacy branch span inverted: " + branch["command"])
        spans[branch["command"]] = (branch["line"], end)
    return spans


# ----------------------------------------------------------------- app side --
def enumerate_v0_routes(app, prefix):
    """Read routes from the live ``url_map``; never from a text search."""
    routes = []
    for rule in app.url_map.iter_rules():
        path = str(rule)
        if not path.startswith(prefix):
            continue
        routes.append({
            "path": path,
            "endpoint": str(rule.endpoint),
            "methods": sorted(method for method in rule.methods
                              if method not in ("HEAD", "OPTIONS")),
            "view": app.view_functions[rule.endpoint],
        })
    routes.sort(key=lambda route: (route["path"], route["endpoint"]))
    return routes


def plant_control_route(app, prefix):
    """Register one synthetic route so a broken enumerator cannot look clean."""
    def route_coverage_control_probe_view():
        return ("probe", 200)

    app.add_url_rule(CONTROL_ROUTE, CONTROL_ENDPOINT, route_coverage_control_probe_view,
                     methods=["POST"])
    seen = {route["path"] for route in enumerate_v0_routes(app, prefix)}
    if CONTROL_ROUTE not in seen:
        raise VerificationError(
            "route enumeration control failed: planted probe %s was not observed"
            % (CONTROL_ROUTE,))
    return route_coverage_control_probe_view


# ---------------------------------------------------------------- citations --
def _docstring_line_range(source_lines):
    """1-based inclusive line range of the handler's own docstring, or None."""
    definition = None
    for index, line in enumerate(source_lines):
        stripped = line.strip()
        if stripped.startswith("def "):
            definition = index
            break
    if definition is None:
        return None
    start = definition
    opener = None
    for index in range(definition, len(source_lines)):
        for quote in DOCSTRING_QUOTES:
            position = source_lines[index].find(quote)
            if position >= 0:
                start = index
                opener = quote
                break
        if opener is not None:
            break
    if opener is None:
        return None
    remainder = source_lines[start].split(opener, 1)[1]
    if opener in remainder:
        return (start, start)
    for index in range(start + 1, len(source_lines)):
        if opener in source_lines[index]:
            # The opener's own line belongs to the docstring: a citation can sit
            # there, and dropping it would silently lose one.
            return (start, index)
    return None


def _resolve_span(start, end, spans):
    """Branch names whose span OVERLAPS the cited span.

    Overlap, not containment, is the right test. A citation such as
    ``command.py:573-623`` names a run of four consecutive branches, so under a
    containment test it would match none and read as "that range is empty" --
    which is the opposite of what is true. Overlap reports what the range
    actually touches: zero branches (a pre-dispatch line such as
    ``command.py:40``, or a line outside ``do_command``), exactly one branch, or
    more than one. Only the middle case grounds a mapping.
    """
    return sorted(name for name, (first, last) in spans.items()
                  if first <= end and start <= last)


def collect_citations(route, spans, branch_names, first_line, file_label):
    """Every explicit branch citation in one handler, with full provenance."""
    citations = []
    body_lines = route["_source_lines"]
    # Offset-indexed, NOT file-line-indexed: comparing the two would make every
    # docstring citation land on the wrong line and silently drop it.
    docstring_offsets = _docstring_line_range(body_lines)

    for offset, line in enumerate(body_lines):
        absolute = first_line + offset
        in_docstring = (docstring_offsets is not None
                        and docstring_offsets[0] <= offset <= docstring_offsets[1])
        for match in CITATION_PATTERN.finditer(line):
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else start
            matched = match.group(0)
            resolved = _resolve_span(start, end, spans)
            citations.append({
                "kind": "line_span",
                "matched_text": matched,
                "file": file_label,
                "line": absolute,
                "in_docstring": in_docstring,
                "cited_first_line": start,
                "cited_last_line": end,
                "context": line.strip(),
                "branches": resolved,
                "resolution": _resolution_name(len(resolved)),
                "negation_markers": _negation_markers(line.strip()),
            })
        if not in_docstring:
            continue
        for token in BACKTICK_PATTERN.findall(line):
            if token in branch_names:
                citations.append({
                    "kind": "docstring_name",
                    "matched_text": "`" + token + "`",
                    "file": file_label,
                    "line": absolute,
                    "in_docstring": True,
                    "cited_first_line": None,
                    "cited_last_line": None,
                    # The citing sentence travels with the mapping. A backtick
                    # mention is evidence the handler CITES the branch, not that
                    # it executes it: several handlers name a branch precisely
                    # to contrast themselves with it ("unlike ``buy`` ...").
                    "context": line.strip(),
                    "branches": [token],
                    "resolution": "resolved",
                    # A backticked name is the WEAK tier. This flag is the
                    # whole reason it is weak: "unlike ``buy``" cites a branch
                    # in order to distinguish itself from it.
                    "negation_markers": _negation_markers(line.strip()),
                })
            elif BARE_SPAN_PATTERN.match(token):
                first, last = token.split("-", 1)
                resolved = _resolve_span(int(first), int(last), spans)
                citations.append({
                    "kind": "bare_line_range",
                    "matched_text": "`" + token + "`",
                    "file": file_label,
                    "line": absolute,
                    "in_docstring": True,
                    "cited_first_line": int(first),
                    "cited_last_line": int(last),
                    "branches": resolved,
                    "resolution": "unresolved_bare_range_without_command_py_prefix",
                    "negation_markers": _negation_markers(line.strip()),
                })
    citations.sort(key=lambda citation: (citation["line"], citation["kind"],
                                          citation["matched_text"]))
    return citations


def _resolution_name(count):
    if count == 1:
        return "resolved"
    if count == 0:
        return "unresolved_no_branch"
    return "ambiguous_multiple_branches"


def _negation_markers(context):
    """Markers found in a citation's verbatim citing line.

    Flag only. Nothing is dropped on the strength of this result: the caller
    still emits the citation, with the markers attached, so a reader can
    adjudicate the sentence. An empty list means "no marker from the explicit
    list appears", which is NOT a claim that the sentence is affirmative.
    """
    lowered = context.lower()
    return sorted(marker for marker in NEGATION_MARKERS if marker in lowered)


# ------------------------------------------------------------------ census --
def build_census(routes, spans, branch_names):
    """Fold per-route citations into the four explicit census tables."""
    branch_coverage = {}
    route_citations = {}
    unresolved = []
    ambiguous = []
    routes_without = []

    for route in routes:
        citations = route["citations"]
        route_citations[route["path"]] = citations
        for citation in citations:
            if citation["resolution"] == "unresolved_no_branch":
                unresolved.append(_citation_record(route["path"], citation))
            elif citation["resolution"] == "ambiguous_multiple_branches":
                ambiguous.append(_citation_record(route["path"], citation))
        grounding = _grounded_pairs(citations)
        if not grounding:
            routes_without.append(route["path"])
        for branch, citation in grounding:
            entry = branch_coverage.setdefault(branch, {"routes": [], "grounding": set()})
            entry["routes"].append({
                "route": route["path"],
                "grounding": citation["kind"],
                "provenance": {
                    "file": citation["file"],
                    "line": citation["line"],
                    "matched_text": citation["matched_text"],
                    "context": citation.get("context", ""),
                    "negation_markers": citation["negation_markers"],
                },
            })
            entry["grounding"].add(citation["kind"])

    for name in branch_names:
        branch_coverage.setdefault(name, {"routes": [], "grounding": set()})

    # "Covered" is the STRONG tier and nothing else: a resolved command.py:NNN
    # line span inside the branch. A backticked branch name does NOT make a
    # branch covered. That tier is reported in full under
    # branches_mentioned_by_name_only, with its verbatim citing line, because a
    # handler naming a branch is frequently naming it to contrast itself with it
    # ("unlike ``buy``", "has no action here at all", "is not in the closed
    # set"). Counting those as coverage inflated the headline; the fix is
    # structural, so a weak citation cannot reach the count at all.
    strong = set()
    for branch, entry in branch_coverage.items():
        if "line_span" in entry["grounding"]:
            strong.add(branch)

    table = []
    for branch in sorted(branch_coverage):
        entry = branch_coverage[branch]
        first, last = spans[branch]
        table.append({
            "branch": branch,
            "span": [first, last],
            "covered": branch in strong,
            "grounding_kinds": sorted(entry["grounding"]),
            "cited_by": sorted(entry["routes"], key=lambda item: (item["route"],
                                                                  item["grounding"],
                                                                  item["provenance"]["line"])),
        })

    multiple = {entry["branch"]: sorted({item["route"] for item in entry["cited_by"]})
                for entry in table if len({item["route"] for item in entry["cited_by"]}) > 1}
    uncovered = [entry["branch"] for entry in table if not entry["covered"]]

    # Name-only mentions: every branch cited by a backticked name but NOT
    # grounded by a line span. Reported with full provenance and the negation
    # flag so a reader can adjudicate each one. Deliberately NOT counted as
    # covered, and deliberately NOT dropped either.
    name_only = {}
    for entry in table:
        branch = entry["branch"]
        if branch in strong:
            continue
        mentions = [item for item in entry["cited_by"]
                    if item["grounding"] == "docstring_name"]
        if not mentions:
            continue
        name_only[branch] = sorted(
            ({
                "route": item["route"],
                "file": item["provenance"]["file"],
                "line": item["provenance"]["line"],
                "matched_text": item["provenance"]["matched_text"],
                "context": item["provenance"]["context"],
                "negation_markers": item["provenance"]["negation_markers"],
            } for item in mentions),
            key=lambda item: (item["route"], item["line"]))

    # The permissive reading is ALSO reported, derived from the same citations,
    # because the two readings disagree and a reader must be able to see both
    # without re-running anything. It is NEVER the headline. Under it a
    # name-only mention counts unless EVERY mention of that branch carries a
    # negation marker -- note this is weaker than it looks, because a branch
    # cited once affirmatively and once with a hedge still counts.
    permissive = set(strong)
    for branch, mentions in name_only.items():
        if any(not mention["negation_markers"] for mention in mentions):
            permissive.add(branch)

    strong_list = sorted(strong)
    return {
        "branch_coverage": table,
        "branches_cited_by_line_span": strong_list,
        "branches_mentioned_by_name_only": name_only,
        "branches_covered_permissive_reading": sorted(permissive),
        "branches_without_cited_route_permissive_reading": sorted(
            set(branch_names) - permissive),
        "branches_without_cited_route": uncovered,
        "routes_without_cited_branch": sorted(routes_without),
        "branches_cited_by_multiple_routes": multiple,
        "ambiguous_citations": ambiguous,
        "unresolved_citations": unresolved,
    }


def _negation_control():
    """Prove the negation detector can fire before trusting it to be silent.

    A detector that cannot flag the crafted positive is inert, and an inert
    detector would emit confident empty ``negation_markers`` lists for every
    real citation -- the most dangerous possible failure, because it looks like
    evidence of affirmation. So this refuses instead.
    """
    fired = _negation_markers(NEGATION_CONTROL_POSITIVE)
    silent = _negation_markers(NEGATION_CONTROL_NEGATIVE)
    if not fired:
        raise VerificationError(
            "negation detector control failed: crafted input %r was not flagged"
            % (NEGATION_CONTROL_POSITIVE,))
    if silent:
        raise VerificationError(
            "negation detector control failed: crafted non-negated input %r was "
            "flagged with %s" % (NEGATION_CONTROL_NEGATIVE, silent))
    return {
        "flagged_crafted_negative": {
            "context": NEGATION_CONTROL_POSITIVE,
            "negation_markers": fired,
            "passed": True,
        },
        "silent_crafted_positive": {
            "context": NEGATION_CONTROL_NEGATIVE,
            "negation_markers": silent,
            "passed": True,
        },
        "note": "the detector must flag the crafted negated sentence and leave "
                "the crafted affirmative one alone; a detector that cannot fire "
                "would render every empty negation_markers list meaningless, so "
                "failure refuses the report rather than emitting it",
    }


def _grounded_pairs(citations):
    """Only unambiguous citations ground a mapping; ambiguity is data, not proof."""
    pairs = []
    for citation in citations:
        if citation["resolution"] != "resolved":
            continue
        pairs.append((citation["branches"][0], citation))
    return pairs


def _citation_record(path, citation):
    return {
        "route": path,
        "kind": citation["kind"],
        "matched_text": citation["matched_text"],
        "file": citation["file"],
        "line": citation["line"],
        "cited_first_line": citation["cited_first_line"],
        "cited_last_line": citation["cited_last_line"],
        "candidate_branches": citation["branches"],
        "resolution": citation["resolution"],
        "negation_markers": citation["negation_markers"],
    }


def collect_routes(app, prefix, spans, branch_names, repo_root):
    """Read route handlers through ``inspect`` and cite their own source."""
    routes = enumerate_v0_routes(app, prefix)
    public = []
    for route in routes:
        view = route.pop("view")
        try:
            source = inspect.getsource(view)
            first_line = inspect.getsourcelines(view)[1]
            source_file = inspect.getsourcefile(view)
        except (OSError, TypeError) as error:
            raise VerificationError("route handler source unavailable: %s" % (error,))
        label = _relative_label(source_file, repo_root)
        route["handler_file"] = label
        route["handler_first_line"] = first_line
        route["_source_lines"] = source.splitlines()
        route["citations"] = collect_citations(route, spans, branch_names,
                                                first_line, label)
        public.append(route)
    return public


def _relative_label(source_file, repo_root):
    if source_file is None:
        raise VerificationError("route handler has no source file")
    try:
        relative = Path(source_file).resolve().relative_to(Path(repo_root).resolve())
    except (OSError, ValueError):
        raise VerificationError("route handler source outside the repository: "
                                + str(source_file))
    # as_posix(), not str(): a native Windows path would serialize as
    # "apps\\compat-api\\compat_service.py" and a POSIX one as
    # "apps/compat-api/compat_service.py", so the committed report would differ
    # by checkout platform. The report must be platform-independent.
    return relative.as_posix()


def run_census(repo_root):
    """Build the whole report, or raise VerificationError. Nothing is written."""
    root = Path(repo_root)
    if not root.is_dir():
        raise VerificationError("repository root invalid")
    # Resolve BEFORE anything can chdir: compat_legacy.initialize() moves the
    # process into the disposable corpus, and a relative root resolved after
    # that would point at the corpus instead of the repository.
    root = root.resolve()

    extractor = load_legacy_extractor(root)
    source = read_text_file(root / LEGACY_SOURCE_FILE, "legacy source")
    spans = legacy_branch_spans(source, extractor)
    branch_names = set(spans)

    previous_cwd = os.getcwd()
    corpus = None
    try:
        for entry in (str(root / SERVICE_RELATIVE), str(root / SERVICE_RELATIVE / "tests")):
            if entry not in sys.path:
                sys.path.insert(0, entry)
        # The Compatibility API boot prints config-patch chatter to stdout on
        # purpose (it is a development aid). Keep it off the report stream.
        with contextlib.redirect_stdout(sys.stderr):
            import compat_legacy
            import compat_service
            import compat_test_harness as harness

            corpus = harness.build_test_corpus()
            boot = compat_legacy.initialize(corpus)
            app = compat_service.create_app(boot)
            routes = collect_routes(app, ROUTE_PREFIX, spans, branch_names, root)

            controls = _run_controls(app, routes, len(spans))
    finally:
        # compat_legacy.initialize chdirs into the corpus and never restores the
        # previous directory; the corpus is about to be deleted, so leaving cwd
        # inside it would strand the caller in a removed directory.
        os.chdir(previous_cwd)
        if corpus is not None:
            harness.remove_corpus(corpus)

    coverage = build_census(routes, spans, branch_names)
    public_routes = []
    for route in routes:
        entry = {key: value for key, value in route.items() if not key.startswith("_")}
        public_routes.append(entry)

    paths = [route["path"] for route in public_routes]
    method_counts = {}
    for route in public_routes:
        for method in route["methods"]:
            method_counts[method] = method_counts.get(method, 0) + 1
    baseline = {
        "v0_rule_count": len(public_routes),
        "distinct_paths": len(set(paths)),
        "method_counts": method_counts,
        "all_paths_share_prefix": all(path.startswith(ROUTE_PREFIX) for path in paths),
        "paths_not_post_only": sorted(route["path"] for route in public_routes
                                      if route["methods"] != ["POST"]),
    }
    baseline["matches_recorded_baseline"] = (
        baseline["v0_rule_count"] == 24
        and baseline["distinct_paths"] == 24
        and method_counts == {"POST": 23, "GET": 1}
        and baseline["paths_not_post_only"] == ["/v0/session"]
    )

    return {
        "schema_version": 1,
        "policy": "route-coverage-census-v1",
        "result": "census",
        "evidence_policy": (
            "A branch is COVERED only when the route handler's own source "
            "cites it with a command.py:NNN line span resolving inside the "
            "branch span. A backticked branch name in a docstring is NOT "
            "coverage: it shows the handler CITES the branch, not that it "
            "implements it, and handlers routinely name a branch to contrast "
            "themselves with it. Name-only mentions are reported in full under "
            "branches_mentioned_by_name_only, each with its verbatim citing line "
            "and a negation_markers flag, for a reader to adjudicate. Naming "
            "similarity is never evidence."
        ),
        "grounding_rule": {
            "covers_branch": ["command.py:NNN line span inside the branch span"],
            "reported_but_not_covered": [
                "branch name in backticks in the handler docstring"],
            "refused": ["route name resembling a branch name",
                        "an ambiguous line span (zero or many branches)",
                        "a backticked line range with no command.py: prefix"],
        },
        "headline_rule": (
            "conservative: a branch is covered ONLY by a resolved command.py:NNN "
            "line span. Name-only mentions are excluded from the headline and "
            "reported in full under branches_mentioned_by_name_only. The "
            "permissive reading (name-only counts unless every mention is "
            "negated) is reported alongside but is never the headline."
        ),
        "negation_rule": {
            "purpose": "flag a citation whose own sentence denies the branch it "
                       "names, so the weak tier can be adjudicated rather than "
                       "counted",
            "scanned_against": "the citation's verbatim citing line, case-insensitively",
            "markers": list(NEGATION_MARKERS),
            "flag_only": "a flagged citation is still reported in full; nothing "
                         "is dropped and no branch is removed from any tier",
            "not_a_claim": "an empty list means no listed marker appeared, not "
                           "that the sentence is affirmative",
        },
        "legacy_branches": {
            "source_file": LEGACY_SOURCE_FILE,
            "extractor": LEGACY_EXTRACTOR_SOURCE + ":extract_command_branches",
            "span_derivation": (
                "each branch spans its own if/elif line to the line before the "
                "next branch; the last branch spans to the end of do_command"
            ),
            "count": len(spans),
            "spans": {name: [spans[name][0], spans[name][1]] for name in sorted(spans)},
        },
        "route_prefix_filter": ROUTE_PREFIX,
        "route_baseline": baseline,
        "controls": controls,
        "routes": public_routes,
        "coverage": coverage,
        "counts": {
            "legacy_branches": len(spans),
            "routes": len(public_routes),
            "branches_covered": sum(1 for entry in coverage["branch_coverage"]
                                    if entry["covered"]),
            "branches_cited_by_line_span": len(coverage["branches_cited_by_line_span"]),
            "branches_mentioned_by_name_only": len(
                coverage["branches_mentioned_by_name_only"]),
            "name_only_mentions_negated": sum(
                1 for mentions in coverage["branches_mentioned_by_name_only"].values()
                for mention in mentions if mention["negation_markers"]),
            "branches_covered_permissive_reading": len(
                coverage["branches_covered_permissive_reading"]),
            "branches_without_cited_route_permissive_reading": len(
                coverage["branches_without_cited_route_permissive_reading"]),
            "branches_without_cited_route": len(coverage["branches_without_cited_route"]),
            "routes_without_cited_branch": len(coverage["routes_without_cited_branch"]),
            "branches_cited_by_multiple_routes": len(coverage["branches_cited_by_multiple_routes"]),
            "ambiguous_citations": len(coverage["ambiguous_citations"]),
            "unresolved_citations": len(coverage["unresolved_citations"]),
        },
    }


def _run_controls(app, routes, branch_count):
    """Controls that can fail. A failed control refuses the whole report."""
    if branch_count != EXPECTED_BRANCH_COUNT:
        raise VerificationError(
            "branch extraction control failed: expected %d branches, resolved %d"
            % (EXPECTED_BRANCH_COUNT, branch_count))
    plant_control_route(app, ROUTE_PREFIX)
    if not routes:
        raise VerificationError(
            "route enumeration control failed: enumeration returned zero %s rules"
            % (ROUTE_PREFIX,))
    # Raises unless the detector both fires on the crafted negated sentence and
    # stays silent on the crafted affirmative one.
    negation = _negation_control()
    return {
        "branch_count": {
            "expected": EXPECTED_BRANCH_COUNT,
            "observed": branch_count,
            "passed": True,
            "note": "guards the reused extractor against silently returning a "
                    "different branch set",
        },
        "planted_route": {
            "path": CONTROL_ROUTE,
            "passed": True,
            "note": "planted on the live app and re-enumerated; a prefix filter "
                    "or an enumeration that cannot see a new rule fails here",
        },
        "enumeration_non_empty": {
            "observed": len(routes),
            "passed": True,
            "note": "a clean zero from an unvalidated instrument is not evidence",
        },
        "negation_detector": negation,
    }


def build_argument_parser():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--repo-root", help="repository root to census (default: current directory)")
    parser.add_argument("--out-path",
                        help="write the deterministic report here; omitted means "
                             "the tool writes nothing at all")
    return parser


def main(argv=None):
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    try:
        report = run_census(args.repo_root or ".")
    except VerificationError as error:
        print(str(error), file=sys.stderr)
        return 2
    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out_path:
        destination = Path(args.out_path)
        if destination.parent and str(destination.parent) not in ("", "."):
            destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())