"""Measure which conversion targets are convertible, and record the refusals.

This tool exists because "the converter ran without error" is not evidence that
the converter generalises. The first-building and first-unit conversions each
proved exactly one target, and both tools carried that target as a module
constant. Before either tool can be pointed at a second target it must be
*parameterised*, and before a milestone may claim asset coverage the population
of convertible targets must be *measured* rather than assumed.

The tool evaluates every convertible-candidate over the whole population and
writes a deterministic report. A refusal by a converter is recorded as data and
the run continues: the census's own failure modes are an unreadable required
input, a missing output root, or an unwritable report -- never a target that the
converter declines to convert.

Nothing here is transcribed. The candidate set is derived from the committed
asset-ID registry (`asset_ids.json`, `item_sprites` entries whose status is
`extracted`) joined against the committed normalized content
(`buildings.json`, `units.json`) on `img_name`. No stem, no `legacy_id`, no
class name, and no count is written into this file.

Containment: every converter invocation is given its own output root beneath an
explicitly required `--out-root`, and this tool never writes into
`conversions.json`, `statuses.json`, or any converted package directory of the
repository. No subprocess, network, server, browser, or Flash runtime is used.

Exit codes: 0 census completed (refusals are data), 2 required input
unreadable or output root/report path missing, 3 a converter raised something
other than a refusal (a genuine tool failure), 1 the report could not be written.
"""

import argparse
import importlib
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import convert_building as building_converter  # noqa: E402
import convert_unit as unit_converter  # noqa: E402

POLICY = "asset-target-census-v1"
SCHEMA_VERSION = 1

EXTRACTED_STATUS = "extracted"
TARGET_PLACEHOLDER = "<target>"
DIGIT_RUN = re.compile(r"\d+")

# The two domains the two converters own. Each maps to the normalized content
# file whose `img_name` resolves the target and to the converter that consumes it.
DOMAINS = (
    ("building", building_converter, "buildings.json"),
    ("unit", unit_converter, "units.json"),
)


def read_json(path, role):
    """Read a committed JSON document, or fail as a genuine tool failure."""
    try:
        data = Path(path).read_bytes()
    except FileNotFoundError:
        raise building_converter.InputError(role + " file missing: " + str(path))
    except OSError:
        raise building_converter.InputError(role + " file unreadable: " + str(path))
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise building_converter.InputError(role + " file not valid JSON: "
                                          + str(path))


def sprite_entries(registry):
    """The `item_sprites` entries of the committed asset-ID registry."""
    if not isinstance(registry, dict):
        raise building_converter.InputError(
            "asset-id registry not an object")
    kinds = registry.get("kinds")
    if not isinstance(kinds, list):
        raise building_converter.InputError(
            "asset-id registry kinds not an array")
    found = [k for k in kinds
             if isinstance(k, dict) and k.get("kind") == "item_sprites"]
    if len(found) != 1:
        raise building_converter.InputError(
            "asset-id registry item_sprites kind count: " + str(len(found)))
    entries = found[0].get("entries")
    if not isinstance(entries, list):
        raise building_converter.InputError(
            "asset-id registry item_sprites entries not an array")
    return entries


def content_rows(document, name):
    """Normalized content rows as a list, or fail as a genuine tool failure."""
    rows = document[name] if isinstance(document, dict) else document
    if not isinstance(rows, list):
        raise building_converter.InputError(
            "normalized content rows not an array: " + name)
    return rows


def rows_by_img_name(rows):
    """Group normalized content rows by `img_name`, as text."""
    grouped = {}
    for row in rows:
        if isinstance(row, dict):
            grouped.setdefault(str(row.get("img_name")), []).append(row)
    return grouped


def candidates(registry, documents):
    """Derive the convertible-candidate population.

    A target is a candidate when its sprite's bitmaps are already recorded as
    extracted *and* its `img_name` resolves to exactly one normalized content
    row. The uniqueness requirement is the converter's own precondition, so a
    stem with two rows would be refused by the converter for a reason that
    says nothing about convertibility, and counting it as a candidate would
    report a refusal class that is really a content ambiguity.
    """
    out = []
    for domain, _converter, content_name in DOMAINS:
        grouped = rows_by_img_name(content_rows(documents[content_name],
                                               content_name))
        for entry in sprite_entries(registry):
            if not isinstance(entry, dict):
                continue
            if entry.get("status") != EXTRACTED_STATUS:
                continue
            stem = str(entry.get("ref"))
            matches = grouped.get(stem) or []
            if len(matches) != 1:
                continue
            row = matches[0]
            out.append({
                "domain": domain,
                "stem": stem,
                "legacy_id": str(row.get("legacy_id")),
            })
    out.sort(key=lambda t: (t["domain"], t["stem"]))
    return out


def refusal_pattern(problem, source):
    """One refusal message reduced to the part that names the refusal.

    Two parts of the converter's own message are target-specific and are
    therefore not part of the class name: the sprite path the message is
    anchored to, and any bare number (a shape id, a fill style, a tag code).
    Everything else is kept verbatim. This is a mechanical reduction of the
    converter's message, not a category invented here: if the converters ever
    word a refusal differently, the pattern changes with them.
    """
    text = problem.replace(source, TARGET_PLACEHOLDER)
    return DIGIT_RUN.sub("#", text)


CONVERTER_BY_DOMAIN = dict((d, c) for d, c, _ in DOMAINS)


def evaluate(target, repo_root, out_root):
    """Run one target's converter and record its verdict as data."""
    domain = target["domain"]
    converter = CONVERTER_BY_DOMAIN[domain]
    source = "assets/sprites/" + target["stem"] + ".swf"
    # One output root per target: the census must not let a converter write
    # into the repository, and must not let one target's outputs stand in for
    # another's.
    target_root = Path(out_root) / target["domain"] / target["stem"]
    if target_root.exists():
        shutil.rmtree(target_root)
    try:
        if domain == "unit":
            converter.run_build(str(repo_root), str(target_root),
                                target["stem"], target["legacy_id"])
        else:
            converter.run_build(str(repo_root), str(target_root),
                                target["stem"])
    except building_converter.ValidationFailure as failure:
        problems = sorted(set(failure.problems))
        patterns = sorted(set(refusal_pattern(p, source) for p in problems))
        return {"verdict": "refused",
                "refusal_class": patterns[0] if len(patterns) == 1 else None,
                "refusal_classes": patterns,
                "problem_count": len(problems),
                "problems": problems}
    record = {"verdict": "converted", "refusal_class": None,
              "refusal_classes": [], "problem_count": 0, "problems": []}
    return record


def build_report(repo_root, out_root):
    """Run the whole population and return the report document."""
    root = Path(repo_root)
    registry = read_json(root / building_converter.REGISTRY_DIR
                         / "asset_ids.json", "asset-id registry")
    documents = {}
    for _domain, _converter, content_name in DOMAINS:
        documents[content_name] = read_json(
            root / building_converter.NORMALIZED_DIR / content_name,
            "normalized content " + content_name)
    population = candidates(registry, documents)

    rows = []
    for target in population:
        record = dict(target)
        record.update(evaluate(target, root, out_root))
        rows.append(record)

    by_domain = {}
    for row in rows:
        bucket = by_domain.setdefault(row["domain"],
                                      {"converted": 0, "refused": 0})
        bucket["converted" if row["verdict"] == "converted" else "refused"] += 1

    classes = {}
    for row in rows:
        for name in row["refusal_classes"]:
            classes.setdefault(name, {"targets": 0,
                                      "domains": set()})
            classes[name]["targets"] += 1
            classes[name]["domains"].add(row["domain"])
    class_rows = [{"refusal_class": name,
                   "targets": data["targets"],
                   "domains": sorted(data["domains"])}
                  for name, data in sorted(classes.items())]

    ambiguous = sorted(row["domain"] + " " + row["stem"]
                       for row in rows
                       if len(row["refusal_classes"]) > 1)

    return {
        "schema_version": SCHEMA_VERSION,
        "policy": POLICY,
        "result": "success",
        "counts": {
            "candidates": len(rows),
            "by_domain": {d: by_domain.get(d, {"converted": 0, "refused": 0})
                          for d, _c, _n in DOMAINS},
            "refused": sum(1 for row in rows if row["verdict"] == "refused"),
            "converted": sum(1 for row in rows if row["verdict"] == "converted"),
            "refusal_classes": len(class_rows),
            "refused_targets_in_several_classes": len(ambiguous),
        },
        "refusal_class_totals": class_rows,
        "refused_targets_in_several_classes": ambiguous,
        "targets": rows,
    }


def build_argument_parser():
    parser = argparse.ArgumentParser(
        description="Measure the convertible-target population.",
        allow_abbrev=False)
    parser.add_argument("--repo-root",
                        help="repository root to read (default: current "
                             "directory)")
    parser.add_argument("--out-root", required=True,
                        help="root beneath which every converter writes; "
                             "required and never defaulted to the repository")
    parser.add_argument("--report", required=True,
                        help="path to write the census report to; required, so "
                             "no run can write a repository file by accident")
    return parser


def write_report(path, document):
    payload = (json.dumps(document, indent=2, sort_keys=True) + "\n").encode(
        "utf-8")
    target = Path(path)
    if target.parent and not target.parent.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)


def main(argv=None):
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    repo_root = args.repo_root or "."
    out_root = Path(args.out_root)
    if not out_root.exists():
        try:
            out_root.mkdir(parents=True, exist_ok=True)
        except OSError:
            print("census output root could not be created: " + str(out_root),
                  file=sys.stderr)
            return 2
    if out_root.resolve() == Path(repo_root).resolve():
        print("census output root must not be the repository root: "
              + str(out_root), file=sys.stderr)
        return 2
    try:
        report = build_report(repo_root, out_root)
    except building_converter.InputError as error:
        print(str(error), file=sys.stderr)
        return 2
    except Exception as error:  # noqa: BLE001
        # Anything a converter raised that is not a refusal is a genuine tool
        # failure, not a target that the census should record and continue past.
        print("census tool failure: " + type(error).__name__ + ": "
              + str(error), file=sys.stderr)
        return 3
    try:
        write_report(args.report, report)
    except OSError:
        print("census report could not be written: " + str(args.report),
              file=sys.stderr)
        return 1
    print(json.dumps({
        "schema_version": SCHEMA_VERSION,
        "policy": POLICY,
        "result": "success",
        "counts": report["counts"],
        "outputs": [args.report],
        "problems": [],
    }, indent=2, sort_keys=True) + "\n", end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
