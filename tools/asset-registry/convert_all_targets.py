"""Mass conversion over the census-convertible target set.

Converts every target the committed `target_census.json` records with
`verdict == "converted"`, writes one `package.json` per target, and
regenerates `conversions.json` and `statuses.json`.

The target set is **derived at run time** from the census document. No
sprite stem, no `legacy_id`, and no count is transcribed into this
file: a hand-copied list of targets is exactly the kind of input that
silently rots when content changes, and the census is the measured
authority for which targets are convertible at all.

Nothing here lifts a refusal. This tool never converts a target the
census records as refused, and it does not re-derive the census: it
reads the committed document. Its own job is narrower, and the one
place it can be wrong in a way that matters is disagreeing with the
census about a convertible target, which is why every target's verdict
is checked against the census and a disagreement is a **distinct
outcome** (exit 4, nothing written) rather than something this run's
own successful conversion is allowed to overrule.

Output form: package directories hold `package.json` and nothing else.
Each `bitmaps[].file` records the extraction output path under
`assets/converted/images/`, and the converter resolves and hashes that
path before anything is written, so the reference is verified rather
than merely recorded.

Containment: `--out-root` is required and is refused unless it is
outside the repository, or `--write-repository` is passed explicitly.
The repository is otherwise read-only input. No subprocess, network,
server, browser, or Flash runtime is used.

Exit codes: 0 every census-convertible target converted and agreed;
2 required input unreadable or the output root refused; 3 a tool
failure (not a converter refusal); 4 a target disagreed with the
census -- nothing written; 1 the report could not be written.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import convert_building as building_converter  # noqa: E402
import convert_unit as unit_converter  # noqa: E402

POLICY = "asset-mass-conversion-v1"
SCHEMA_VERSION = 1

CENSUS_VERDICT_CONVERTED = "converted"

# The domain each census row selects, and the converter that owns it.
# Both constants are the converters' own, so this file names no target:
# a new domain would have to be declared by a converter.
DOMAIN_CONVERTERS = {
    "building": building_converter,
    "unit": unit_converter,
}
CONVERTED_DIR_BY_DOMAIN = {
    "building": building_converter.CONVERTED_BUILDINGS_DIR,
    "unit": unit_converter.CONVERTED_UNITS_DIR,
}
CONTENT_FILE_BY_DOMAIN = {
    "building": building_converter.BUILDINGS_FILE,
    "unit": unit_converter.UNITS_FILE,
}
CONVERTER_POLICY_BY_DOMAIN = {
    "building": building_converter.POLICY,
    "unit": unit_converter.POLICY,
}
CONTENT_INPUT_KEY_BY_DOMAIN = {
    "building": "buildings",
    "unit": "units",
}
CONTENT_VERSION_KEY_BY_DOMAIN = {
    "building": "buildings_content_version",
    "unit": "units_content_version",
}


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


def census_targets(census):
    """The census rows this tool is responsible for, in a stable order.

    Only `verdict == "converted"` rows are selected. Refused rows are not
    re-run and not converted: a refusal the census measured stays refused
    here, which is what makes this tool incapable of lifting a refusal
    class even by accident.
    """
    if not isinstance(census, dict):
        raise building_converter.InputError("target census not an object")
    rows = census.get("targets")
    if not isinstance(rows, list):
        raise building_converter.InputError("target census targets not an array")
    selected = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("verdict") != CENSUS_VERDICT_CONVERTED:
            continue
        if row.get("domain") not in DOMAIN_CONVERTERS:
            raise building_converter.InputError(
                "target census converted row has unknown domain: "
                + repr(row.get("domain")))
        if not isinstance(row.get("stem"), str) or not row["stem"]:
            raise building_converter.InputError(
                "target census converted row has no stem")
        selected.append(row)
    selected.sort(key=lambda row: (row["domain"], row["stem"]))
    return selected, len(rows)


def census_fingerprint(path):
    """Raw sha256 of the census document this run read.

    Recorded so the report names the census it derived from rather than
    leaving the reader to assume it was the committed one.
    """
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def convert_one(root, out_root, row):
    """Convert one target and return (entry, package, package_payload, statuses).

    Raises the converter's `ValidationFailure` when the target refuses,
    which the caller turns into a disagreement rather than into a
    success.

    The converter's own `document` is deliberately discarded and rebuilt by
    `merge_entry`: that document was merged into whatever was on disk under
    `--out-root`, which is not necessarily this run's accumulating manifest.
    The converter's `package` is kept, because its `content_version` is the
    fingerprint this run must stamp -- reading it back from the package the
    converter just produced avoids re-hashing three input documents 290
    times, and it cannot disagree with the package it stamps because it is
    the same value the converter computed.
    """
    domain = row["domain"]
    converter = DOMAIN_CONVERTERS[domain]
    stem = row["stem"]
    if domain == "unit":
        package, package_payload, _document, statuses = converter.build_package(
            str(root), str(out_root), stem, row["legacy_id"])
    else:
        package, package_payload, _document, statuses = converter.build_package(
            str(root), str(out_root), stem)
    entry = building_converter.conversion_entry(
        (CONVERTED_DIR_BY_DOMAIN[domain] / stem).as_posix(), stem,
        package_payload, len(package["bitmaps"]),
        CONVERTER_POLICY_BY_DOMAIN[domain])
    return entry, package, package_payload, statuses


def merge_entry(root, base_document, row, entry, content_version):
    """Fold one target's entry into the accumulating conversion manifest.

    `base_document` is passed explicitly so the manifest is accumulated in
    memory and written once; without it the merge reads and rewrites the
    file per target, and 290 targets would each re-read a document the
    previous 289 had just replaced.
    """
    domain = row["domain"]
    return building_converter.merge_conversion_document(
        root, entry, {
            CONTENT_INPUT_KEY_BY_DOMAIN[domain]:
                CONTENT_FILE_BY_DOMAIN[domain].as_posix(),
            "inspection": (building_converter.REGISTRY_DIR
                           / "inspection.json").as_posix(),
            "extraction": (building_converter.REGISTRY_DIR
                           / "image_extraction.json").as_posix(),
            CONTENT_VERSION_KEY_BY_DOMAIN[domain]: content_version,
        }, CONVERTER_POLICY_BY_DOMAIN[domain], base=base_document)


def write_package(out_root, row, package_payload):
    """Write one package.json and clear the directory of anything else.

    Clearing is delegated to the converters' own
    `remove_foreign_payloads` so this tool cannot grow a second, weaker
    spelling of the rule that a package directory holds only its manifest.
    """
    package_dir = Path(out_root) / CONVERTED_DIR_BY_DOMAIN[row["domain"]] \
        / row["stem"]
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "package.json").write_bytes(package_payload)
    return building_converter.remove_foreign_payloads(package_dir)


def evaluate(repo_root, out_root, census_path):
    """Convert every census-convertible target, writing nothing.

    Returns the accumulating manifest, the merged statuses, the per-target
    records, and the disagreements. Nothing reaches the filesystem here,
    so a disagreement is discovered before any output exists rather than
    after a partial manifest has been committed.
    """
    root = Path(repo_root)
    census = read_json(census_path, "target census")
    rows, census_rows = census_targets(census)
    document = None
    statuses = {}
    targets = []
    disagreements = []
    payloads = []
    for row in rows:
        domain = row["domain"]
        try:
            entry, package, package_payload, merged_statuses = convert_one(
                root, out_root, row)
        except building_converter.ValidationFailure as failure:
            record = {"domain": domain, "stem": row["stem"],
                      "census_verdict": row["verdict"],
                      "run_verdict": "refused",
                      "agreed": False,
                      "problems": sorted(set(failure.problems))}
            targets.append(record)
            disagreements.append(record)
            continue
        document = merge_entry(root, document, row, entry,
                               package["content_version"])
        statuses.update(merged_statuses)
        payloads.append((row, package_payload))
        targets.append({
            "domain": domain,
            "stem": row["stem"],
            "census_verdict": row["verdict"],
            "run_verdict": "converted",
            "agreed": True,
            "directory": entry["directory"],
            "package_sha256": entry["package_sha256"],
            "bitmaps": entry["bitmaps"],
            "output_bytes": entry["output_bytes"],
            "content_version": package["content_version"],
        })
    return {
        "schema_version": SCHEMA_VERSION,
        "policy": POLICY,
        "census": {
            "path": Path(census_path).as_posix(),
            "sha256": census_fingerprint(census_path),
            "rows": census_rows,
            "census_convertible": len(rows),
        },
        "counts": {
            "selected": len(rows),
            "converted": len(payloads),
            "disagreements": len(disagreements),
            "census_rows_not_selected": census_rows - len(rows),
            "bitmaps_referenced": sum(row["bitmaps"] for row in targets
                                      if row["agreed"]),
            "package_bytes": sum(row["output_bytes"] for row in targets
                                 if row["agreed"]),
        },
        "disagreements": disagreements,
        "document": document,
        "statuses": statuses,
        "targets": targets,
        "payloads": payloads,
    }


def write_outputs(out_root, outcome):
    """Write every package, then the shared manifest and statuses once."""
    removed = []
    for row, package_payload in outcome["payloads"]:
        for name in write_package(out_root, row, package_payload):
            removed.append(row["directory"] + "/" + name)
    conversions_payload = (json.dumps(outcome["document"], indent=2,
                                      sort_keys=True) + "\n").encode("utf-8")
    statuses_payload = (json.dumps({"schema_version": SCHEMA_VERSION,
                                    "policy": "asset-statuses-v1",
                                    "statuses": outcome["statuses"]},
                                   indent=2, sort_keys=True)
                         + "\n").encode("utf-8")
    (Path(out_root) / building_converter.REGISTRY_DIR).mkdir(parents=True,
                                                             exist_ok=True)
    (Path(out_root) / building_converter.CONVERSIONS_FILE).write_bytes(
        conversions_payload)
    (Path(out_root) / building_converter.REGISTRY_DIR
     / "statuses.json").write_bytes(statuses_payload)
    return {
        "conversions": {
            "file": building_converter.CONVERSIONS_FILE.as_posix(),
            "bytes": len(conversions_payload),
            "sha256": hashlib.sha256(conversions_payload).hexdigest(),
        },
        "statuses": {
            "file": (building_converter.REGISTRY_DIR / "statuses.json").as_posix(),
            "bytes": len(statuses_payload),
            "sha256": hashlib.sha256(statuses_payload).hexdigest(),
        },
        "removed_files": sorted(removed),
    }


def write_report(path, document):
    payload = (json.dumps(document, indent=2, sort_keys=True) + "\n").encode(
        "utf-8")
    target = Path(path)
    if target.parent and not target.parent.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)


def build_argument_parser():
    parser = argparse.ArgumentParser(
        description="Convert every census-convertible target.",
        allow_abbrev=False)
    parser.add_argument("--repo-root",
                        help="repository root to read (default: current "
                             "directory)")
    parser.add_argument("--out-root", required=True,
                        help="root to write packages into; required and never "
                             "defaulted, because a defaulted output root is "
                             "how a run writes into the repository by "
                             "accident")
    parser.add_argument("--write-repository", action="store_true",
                        help="explicitly allow --out-root to be the "
                             "repository root or inside it; without this flag "
                             "such a root is refused")
    parser.add_argument("--census",
                        help="committed target census to derive the target set "
                             "from (default: tools/asset-registry/"
                             "target_census.json under --repo-root)")
    parser.add_argument("--report", required=True,
                        help="path to write the per-target run report to; "
                             "required, so no run can write a repository file "
                             "by accident")
    return parser


def main(argv=None):
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    repo_root = args.repo_root or "."
    out_root = Path(args.out_root)
    census_path = Path(args.census) if args.census else (
        Path(repo_root) / building_converter.REGISTRY_DIR / "target_census.json")
    repo_root_path = Path(repo_root).resolve()
    out_root_path = out_root.resolve()
    inside_repository = (out_root_path == repo_root_path
                         or repo_root_path in out_root_path.parents)
    if inside_repository and not args.write_repository:
        print("mass conversion output root must not be the repository root or "
              "inside it without --write-repository: " + str(out_root),
              file=sys.stderr)
        return 2
    try:
        outcome = evaluate(repo_root, out_root, census_path)
    except building_converter.InputError as error:
        print(str(error), file=sys.stderr)
        return 2
    except Exception as error:  # noqa: BLE001
        # A converter that raised something other than a refusal is a tool
        # failure, not a target this run should record and continue past.
        print("mass conversion tool failure: " + type(error).__name__ + ": "
              + str(error), file=sys.stderr)
        return 3
    if outcome["disagreements"]:
        # Fail closed, and report the disagreement as its own outcome: a
        # census-convertible target this run refused means the run's own
        # verdict may not stand in for the census's.
        outcome.pop("document", None)
        outcome.pop("statuses", None)
        outcome.pop("payloads", None)
        outcome["result"] = "census-disagreement"
        outcome["outputs"] = []
        try:
            write_report(args.report, outcome)
        except OSError:
            print("mass conversion report could not be written: "
                  + str(args.report), file=sys.stderr)
            return 1
        print(json.dumps({
            "schema_version": SCHEMA_VERSION,
            "policy": POLICY,
            "result": "census-disagreement",
            "counts": outcome["counts"],
            "outputs": [],
            "problems": [row["domain"] + " " + row["stem"]
                         for row in outcome["disagreements"]],
        }, indent=2, sort_keys=True) + "\n", end="")
        return 4
    outputs = write_outputs(out_root, outcome)
    outcome.pop("document", None)
    outcome.pop("statuses", None)
    outcome.pop("payloads", None)
    outcome["result"] = "success"
    outcome["outputs"] = outputs
    try:
        write_report(args.report, outcome)
    except OSError:
        print("mass conversion report could not be written: "
              + str(args.report), file=sys.stderr)
        return 1
    print(json.dumps({
        "schema_version": SCHEMA_VERSION,
        "policy": POLICY,
        "result": "success",
        "counts": outcome["counts"],
        "outputs": [building_converter.CONVERSIONS_FILE.as_posix(),
                    (building_converter.REGISTRY_DIR / "statuses.json").as_posix()],
        "problems": [],
    }, indent=2, sort_keys=True) + "\n", end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
