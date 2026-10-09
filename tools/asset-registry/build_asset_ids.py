"""Build tools/asset-registry/asset_ids.json.

Joins every distinct content asset reference (images, item_sprites,
magic_sprites, sounds) with the committed corpus registry and the M4
conversion and extraction evidence, assigning each reference exactly one
runtime status from a closed vocabulary:

    converted       an assembled conversion package directory exists
    extracted       bitmap outputs are recorded for the source SWF
    passthrough     the source file is already a runtime-readable format
    pending         the source exists but no runtime output exists yet
    ambiguous       no corpus file matches the reference's own path or its
                    basename uniquely (unreachable for the committed corpus)
    missing_source  the corpus contains no matching source file

The join rules and reference extraction mirror build_registry.py's coverage
step exactly, and the recomputed numbers are reconciled against the
committed coverage.json before anything is written; conversions.json and
image_extraction.json decide which resolved references carry a runtime path.
The output is deterministic: byte-identical on rerun without tree changes.
Validation failures exit 1 without writing; invalid inputs exit 2.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import build_registry as source

REGISTRY_DIR = Path("tools") / "asset-registry"
REGISTRY_FILE = REGISTRY_DIR / "registry.json"
COVERAGE_FILE = REGISTRY_DIR / "coverage.json"
CONVERSIONS_FILE = REGISTRY_DIR / "conversions.json"
IMAGE_EXTRACTION_FILE = REGISTRY_DIR / "image_extraction.json"
OUTPUT_FILE = REGISTRY_DIR / "asset_ids.json"

SCHEMA_VERSION = 1
POLICY = "asset-id-registry-v1"

# Output order of the kind blocks (array order survives sort_keys).
KIND_ORDER = ("images", "item_sprites", "magic_sprites", "sounds")
STATUSES = ("converted", "extracted", "passthrough", "pending", "ambiguous",
            "missing_source")
# Source extensions a modern runtime can load without conversion.
RUNTIME_EXTENSIONS = (".jpg", ".jpeg", ".png", ".mp3")
# The conversion package root every extracted runtime directory lives under.
EXTRACTED_PREFIX = "assets/converted/images/"

RULES = {
    "images": source.IMAGE_RULE,
    "item_sprites": "assets/sprites/<stem>.swf",
    "magic_sprites": "assets/magic/<stem>.swf",
    "sounds": "assets/sounds/<stem>.mp3",
}


class InputError(source.InputError):
    """Invalid input or unsupported shape: exit 2."""


class ValidationFailure(source.ValidationFailure):
    """Reconciliation failure: exit 1 without writing output."""


def read_input(root, relative, role, inputs_records):
    """Read one JSON input as bytes, record its digest, and parse it."""
    path = Path(root) / relative
    try:
        data = path.read_bytes()
    except OSError:
        raise InputError("file missing: " + relative.as_posix())
    try:
        document = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise InputError("not valid json: " + relative.as_posix())
    inputs_records.append({
        "file": relative.as_posix(),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    })
    return document


def record_input(root, relative, inputs_records):
    """Record the digest of an input file that another reader parses."""
    try:
        data = (Path(root) / relative).read_bytes()
    except OSError:
        raise InputError("file missing: " + relative.as_posix())
    inputs_records.append({
        "file": relative.as_posix(),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    })


def require_object(document, relative, *fields):
    if not isinstance(document, dict):
        raise InputError(relative.as_posix() + " not a json object")
    for field in fields:
        if field not in document:
            raise InputError(relative.as_posix() + " missing field: " + field)
    return document


def join_coverage_tiers(registry_paths, image_refs, item_refs, magic_refs,
                        sound_refs):
    """Recompute the four coverage joins exactly as build_registry does."""
    basenames = {}
    for path in registry_paths:
        basenames.setdefault(path.rsplit("/", 1)[-1], []).append(path)

    item_joined = ["assets/sprites/" + ref + ".swf" for ref in item_refs]
    magic_joined = ["assets/magic/" + ref + ".swf" for ref in magic_refs]
    sound_joined = ["assets/sounds/" + ref + ".mp3" for ref in sound_refs]

    image_tiers = source.join_image_refs(image_refs, registry_paths, basenames)
    image_candidates = {}
    for ref in image_refs:
        if ref in image_tiers["files"]:
            image_candidates[ref] = [image_tiers["files"][ref]]
        elif ref in image_tiers["fallback_ambiguous"]:
            image_candidates[ref] = sorted(
                basenames.get(ref.rsplit("/", 1)[-1], []))
        else:
            image_candidates[ref] = []

    resolved = {
        "item_sprites": [ref for ref, joined in zip(item_refs, item_joined)
                         if joined in registry_paths],
        "magic_sprites": [ref for ref, joined in zip(magic_refs, magic_joined)
                          if joined in registry_paths],
        "sounds": [ref for ref, joined in zip(sound_refs, sound_joined)
                   if joined in registry_paths],
        "images": (list(image_tiers["path_resolved"])
                   + list(image_tiers["fallback_resolved"])),
    }
    missing = {
        "item_sprites": sorted({ref for ref, joined in zip(item_refs,
                                                           item_joined)
                                if joined not in registry_paths}),
        "magic_sprites": sorted({ref for ref, joined in zip(magic_refs,
                                                            magic_joined)
                                 if joined not in registry_paths}),
        "sounds": sorted({ref for ref, joined in zip(sound_refs, sound_joined)
                          if joined not in registry_paths}),
        "images": sorted(set(image_tiers["missing"])),
    }
    return resolved, missing, image_candidates, image_tiers


def reconcile(coverage, references, resolved, missing, image_tiers):
    """Compare the recomputed joins with the committed coverage report."""
    problems = []
    domains = coverage.get("domains")
    if not isinstance(domains, dict):
        return ["coverage mismatch: domains section missing or not an object"]
    for kind in KIND_ORDER:
        recorded = domains.get(kind)
        if not isinstance(recorded, dict):
            problems.append("coverage mismatch: domain section missing: "
                            + kind)
            continue
        pairs = (
            ("references", len(references[kind])),
            ("distinct_references", len(set(references[kind]))),
            ("resolved", len(resolved[kind])),
        )
        for field, recomputed in pairs:
            if recorded.get(field) != recomputed:
                problems.append(
                    "coverage mismatch: %s %s recorded %r, recomputed %d"
                    % (kind, field, recorded.get(field), recomputed))
        recorded_missing = recorded.get("missing")
        if not isinstance(recorded_missing, list) \
                or sorted(recorded_missing) != missing[kind]:
            problems.append(
                "coverage mismatch: %s missing list recorded %r, recomputed %r"
                % (kind, recorded_missing, missing[kind]))
        if kind == "images":
            for field, recomputed in (
                    ("path_resolved", len(image_tiers["path_resolved"])),
                    ("fallback_resolved",
                     len(image_tiers["fallback_resolved"])),
                    ("fallback_ambiguous",
                     len(image_tiers["fallback_ambiguous"]))):
                if recorded.get(field) != recomputed:
                    problems.append(
                        "coverage mismatch: images %s recorded %r, recomputed %d"
                        % (field, recorded.get(field), recomputed))
            for field, tier in (("fallback_resolved_refs", "fallback_resolved"),
                                ("fallback_ambiguous_refs",
                                 "fallback_ambiguous")):
                if recorded.get(field) != sorted(image_tiers[tier]):
                    problems.append(
                        "coverage mismatch: images %s list differs from the "
                        "recomputed join" % field)
    return problems


def load_conversions(root, inputs_records):
    document = require_object(
        read_input(root, CONVERSIONS_FILE, "conversions", inputs_records),
        CONVERSIONS_FILE, "packages")
    packages = document["packages"]
    if not isinstance(packages, list):
        raise InputError("conversions.json packages not an array")
    by_legacy_id = {}
    for package in packages:
        if not isinstance(package, dict) \
                or not isinstance(package.get("legacy_id"), str) \
                or not isinstance(package.get("directory"), str):
            raise InputError("conversions.json package malformed")
        if package["legacy_id"] in by_legacy_id:
            raise InputError("conversions.json repeats legacy_id: "
                             + package["legacy_id"])
        by_legacy_id[package["legacy_id"]] = package["directory"]
    return by_legacy_id


def load_extraction_dirs(root, inputs_records):
    """source SWF path -> set of output directories (only with outputs)."""
    document = require_object(
        read_input(root, IMAGE_EXTRACTION_FILE, "image extraction",
                   inputs_records),
        IMAGE_EXTRACTION_FILE, "bitmaps")
    bitmaps = document["bitmaps"]
    if not isinstance(bitmaps, list):
        raise InputError("image_extraction.json bitmaps not an array")
    mapping = {}
    for record in bitmaps:
        if not isinstance(record, dict):
            raise InputError("image_extraction.json bitmap record malformed")
        origin = record.get("source")
        outputs = record.get("outputs")
        if not isinstance(origin, str) or not origin:
            raise InputError("image_extraction.json record has no source")
        if not isinstance(outputs, list):
            raise InputError("image_extraction.json record outputs malformed")
        directories = mapping.setdefault(origin, set())
        for output in outputs:
            if not isinstance(output, dict) \
                    or not isinstance(output.get("file"), str):
                raise InputError(
                    "image_extraction.json output record malformed: "
                    + origin)
            file = output["file"]
            if not file.startswith(EXTRACTED_PREFIX):
                raise InputError(
                    "extraction output outside images root: " + file)
            directories.add(file.rsplit("/", 1)[0])
    return {origin: directories for origin, directories in mapping.items()
            if directories}


def corpus_digest(root, relative):
    try:
        data = (Path(root) / relative).read_bytes()
    except OSError:
        raise InputError("file missing: " + relative)
    return hashlib.sha256(data).hexdigest()


def require_corpus_file(root, relative):
    if not (Path(root) / relative).is_file():
        raise InputError("file missing: " + relative)


def classify_swf(root, ref, joined, registry_paths, conversions,
                 extraction_dirs):
    """Status for one item/magic sprite reference (SWF source)."""
    if joined not in registry_paths:
        return {"status": "missing_source", "source": None,
                "source_sha256": None, "runtime": None}
    require_corpus_file(root, joined)
    digest = corpus_digest(root, joined)
    if ref in conversions:
        directory = conversions[ref]
        if not (Path(root) / directory).is_dir():
            raise InputError("conversion package directory missing: "
                             + directory)
        return {"status": "converted", "source": joined,
                "source_sha256": digest, "runtime": directory}
    directories = extraction_dirs.get(joined, set())
    if directories:
        if len(directories) != 1:
            raise ValidationFailure([
                "extraction outputs span multiple directories for " + joined,
            ])
        return {"status": "extracted", "source": joined,
                "source_sha256": digest,
                "runtime": sorted(directories)[0]}
    return {"status": "pending", "source": joined,
            "source_sha256": digest, "runtime": None}


def classify_single_source(root, sole, extraction_dirs):
    """Status for a sole corpus hit that is not already runtime-readable."""
    require_corpus_file(root, sole)
    digest = corpus_digest(root, sole)
    if sole.endswith(".swf"):
        directories = extraction_dirs.get(sole, set())
        if len(directories) == 1:
            return {"status": "extracted", "source": sole,
                    "source_sha256": digest,
                    "runtime": sorted(directories)[0]}
        if len(directories) > 1:
            raise ValidationFailure([
                "extraction outputs span multiple directories for " + sole,
            ])
    return {"status": "pending", "source": sole,
            "source_sha256": digest, "runtime": None}


def build_kind_entries(root, kind, references, registry_paths, conversions,
                       extraction_dirs, image_candidates):
    """Entries for one kind: one per distinct reference, sorted by ref."""
    counts = {}
    for ref in references:
        counts[ref] = counts.get(ref, 0) + 1
    entries = []
    for ref in sorted(counts):
        entry = {"ref": ref, "reference_count": counts[ref]}
        if kind == "images":
            candidates = image_candidates.get(ref, [])
            if not candidates:
                verdict = {"status": "missing_source", "source": None,
                           "source_sha256": None, "runtime": None}
            elif len(candidates) > 1:
                verdict = {"status": "ambiguous", "source": None,
                           "source_sha256": None, "runtime": None,
                           "candidates": candidates}
            else:
                sole = candidates[0]
                if sole.lower().endswith(RUNTIME_EXTENSIONS):
                    require_corpus_file(root, sole)
                    verdict = {"status": "passthrough", "source": sole,
                               "source_sha256": corpus_digest(root, sole),
                               "runtime": sole}
                else:
                    verdict = classify_single_source(
                        root, sole, extraction_dirs)
        elif kind == "sounds":
            joined = "assets/sounds/" + ref + ".mp3"
            if joined not in registry_paths:
                verdict = {"status": "missing_source", "source": None,
                           "source_sha256": None, "runtime": None}
            else:
                require_corpus_file(root, joined)
                digest = corpus_digest(root, joined)
                if joined.lower().endswith(RUNTIME_EXTENSIONS):
                    verdict = {"status": "passthrough", "source": joined,
                               "source_sha256": digest, "runtime": joined}
                else:
                    verdict = {"status": "pending", "source": joined,
                               "source_sha256": digest, "runtime": None}
        else:
            joined = (("assets/sprites/" + ref + ".swf") if kind == "item_sprites"
                      else "assets/magic/" + ref + ".swf")
            verdict = classify_swf(root, ref, joined, registry_paths,
                                   conversions, extraction_dirs)
        entry.update(verdict)
        entries.append(entry)
    return entries


def validate_entries(kind, entries, distinct_count):
    """Per-kind invariants: vocabulary, uniqueness, runtime contract."""
    problems = []
    seen = set()
    by_status = {}
    for entry in entries:
        ref = entry["ref"]
        if ref in seen:
            problems.append("%s repeats ref: %s" % (kind, ref))
        seen.add(ref)
        status = entry.get("status")
        if status not in STATUSES:
            problems.append("%s/%s has foreign status: %r"
                            % (kind, ref, status))
            continue
        by_status[status] = by_status.get(status, 0) + 1
        runtime = entry.get("runtime")
        if status in ("converted", "extracted", "passthrough"):
            if not isinstance(runtime, str) or not runtime:
                problems.append("%s/%s claims %s without a runtime path"
                                % (kind, ref, status))
        elif runtime:
            problems.append("%s/%s with %s must not claim a runtime path"
                            % (kind, ref, status))
        if status == "ambiguous":
            candidates = entry.get("candidates")
            if not isinstance(candidates, list) or not candidates \
                    or candidates != sorted(candidates):
                problems.append("%s/%s ambiguous without sorted candidates"
                                % (kind, ref))
    if len(entries) != distinct_count:
        problems.append("%s entry count %d != distinct references %d"
                        % (kind, len(entries), distinct_count))
    return problems, by_status


def run_build(repo_root, out_root):
    """Build the asset ID registry; write only OUTPUT_FILE under out_root."""
    root = Path(repo_root)
    inputs_records = []
    registry = require_object(
        read_input(root, REGISTRY_FILE, "registry", inputs_records),
        REGISTRY_FILE, "entries")
    coverage = require_object(
        read_input(root, COVERAGE_FILE, "coverage", inputs_records),
        COVERAGE_FILE, "domains")
    registry_entries = registry["entries"]
    if not isinstance(registry_entries, list):
        raise InputError("registry.json entries not an array")
    registry_paths = set()
    for entry in registry_entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"),
                                                         str):
            raise InputError("registry.json entry malformed")
        registry_paths.add(entry["path"])

    item_refs = source.extract_item_sprite_refs(root)
    magic_refs = source.extract_field_refs(root, source.MAGICS_FILE,
                                            "img_name")
    sound_refs = source.extract_field_refs(root, source.SOUNDS_FILE, "file")
    image_refs = source.extract_field_refs(root, source.IMAGES_FILE, "path")
    for relative in (tuple(source.ITEM_FILES) + (source.MAGICS_FILE,
                                                 source.SOUNDS_FILE,
                                                 source.IMAGES_FILE)):
        record_input(root, relative, inputs_records)
    references = {
        "images": image_refs,
        "item_sprites": item_refs,
        "magic_sprites": magic_refs,
        "sounds": sound_refs,
    }

    resolved, missing, image_candidates, image_tiers = join_coverage_tiers(
        registry_paths, image_refs, item_refs, magic_refs, sound_refs)
    problems = reconcile(coverage, references, resolved, missing, image_tiers)
    if problems:
        raise ValidationFailure(problems)

    conversions = load_conversions(root, inputs_records)
    extraction_dirs = load_extraction_dirs(root, inputs_records)

    kinds = []
    by_kind = {}
    by_status = {status: 0 for status in STATUSES}
    entries_total = 0
    for kind in KIND_ORDER:
        entries = build_kind_entries(
            root, kind, references[kind], registry_paths, conversions,
            extraction_dirs, image_candidates)
        entry_problems, kind_statuses = validate_entries(
            kind, entries, len(set(references[kind])))
        if entry_problems:
            raise ValidationFailure(entry_problems)
        if kind == "item_sprites":
            converted = sorted(entry["ref"] for entry in entries
                               if entry["status"] == "converted")
            if converted != sorted(conversions):
                raise ValidationFailure([
                    "converted set %r does not equal conversion packages %r"
                    % (converted, sorted(conversions)),
                ])
        kinds.append({"kind": kind, "rule": RULES[kind], "entries": entries})
        by_kind[kind] = kind_statuses
        for status, count in kind_statuses.items():
            by_status[status] += count
        entries_total += len(entries)

    counts = {
        "entries": entries_total,
        "references": {kind: len(references[kind]) for kind in KIND_ORDER},
        "distinct": {kind: len(set(references[kind])) for kind in KIND_ORDER},
        "resolved_references": {kind: len(resolved[kind])
                                for kind in KIND_ORDER},
        "by_kind": by_kind,
        "by_status": by_status,
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "policy": POLICY,
        "result": "success",
        "inputs": sorted(inputs_records, key=lambda record: record["file"]),
        "counts": counts,
        "kinds": kinds,
    }
    encoded = (json.dumps(payload, indent=2, sort_keys=True)
               + "\n").encode("utf-8")
    destination = Path(out_root) / OUTPUT_FILE
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(encoded)
    return payload, {
        "file": OUTPUT_FILE.as_posix(),
        "bytes": len(encoded),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }


def build_argument_parser():
    parser = argparse.ArgumentParser(description=__doc__,
                                     allow_abbrev=False)
    parser.add_argument("--repo-root",
                        help="repository root to read (default: current directory)")
    parser.add_argument("--out-root",
                        help="root to write asset_ids.json under (default: same as repo root)")
    return parser


def main(argv=None):
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    repo_root = args.repo_root or "."
    out_root = args.out_root or repo_root
    try:
        payload, digest = run_build(repo_root, out_root)
    except source.ValidationFailure as failure:
        report = {
            "schema_version": SCHEMA_VERSION,
            "policy": POLICY,
            "result": "validation-failed",
            "counts": {},
            "problems": list(getattr(failure, "problems",
                                     [str(failure)])),
        }
        print(json.dumps(report, indent=2, sort_keys=True) + "\n", end="")
        return 1
    except source.InputError as error:
        print(str(error), file=sys.stderr)
        return 2
    report = {
        "schema_version": SCHEMA_VERSION,
        "policy": POLICY,
        "result": "success",
        "counts": payload["counts"],
        "outputs": [digest["file"]],
        "problems": [],
    }
    print(json.dumps(report, indent=2, sort_keys=True) + "\n", end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
