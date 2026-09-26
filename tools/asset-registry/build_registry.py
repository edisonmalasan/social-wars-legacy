"""Offline asset-registry builder and validator (M4 slice 1: observe/record).

Enumerates the worktree asset corpus (fixed extension set, explicit
directory exclusions) with per-file POSIX path, size, SHA-256,
extension, directory class, and default status `registered`; extracts
asset references from the committed normalized game-content package;
joins them with documented per-domain rules; and writes
`tools/asset-registry/registry.json` plus `tools/asset-registry/coverage.json`
with a JSON report on stdout. Hashes identify worktree bytes and are
documented as distinct from the baseline Git-blob hashes owned by
`legacy-manifest.json`.

No SWF parsing, no conversion, no asset mutation, no Flash execution:
every source asset remains byte-identical. Standard library only: no
legacy application import, no runtime save reads, no network, server,
browser, subprocess, or Flash activity.

Exit 0 prints a success report and writes both outputs. Exit 1 prints a
`validation-failed` report and writes nothing. Exit 2 reports invalid
input or unsupported shapes on stderr.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

POLICY = "asset-registry-v1"
SCHEMA_VERSION = 1

INCLUDE_EXTENSIONS = (".swf", ".jpg", ".jpeg", ".png", ".mp3", ".wav", ".gif")
EXCLUDE_PREFIXES = ("./.git/", "./saves/", "./temp/", "./new_assets/",
                    "./assets/converted/",
                    "./build/bundle", "./build/dist", "./build/work",
                    "./apps/")

NORMALIZED_DIR = Path("packages") / "game-content" / "normalized"
REGISTRY_DIR = Path("tools") / "asset-registry"
SCHEMA_DIR = REGISTRY_DIR / "schemas"
REGISTRY_SCHEMA_FILE = SCHEMA_DIR / "registry.schema.json"
ENTRY_SCHEMA_FILE = SCHEMA_DIR / "registry_entry.schema.json"
COVERAGE_SCHEMA_FILE = SCHEMA_DIR / "coverage.schema.json"
REGISTRY_FILE = REGISTRY_DIR / "registry.json"
COVERAGE_FILE = REGISTRY_DIR / "coverage.json"

ITEM_FILES = (NORMALIZED_DIR / "buildings.json",
              NORMALIZED_DIR / "units.json",
              NORMALIZED_DIR / "specials.json")
MAGICS_FILE = NORMALIZED_DIR / "magics.json"
SOUNDS_FILE = NORMALIZED_DIR / "sounds.json"
IMAGES_FILE = NORMALIZED_DIR / "images.json"

MAX_SOURCE_BYTES = 4 * 1024 * 1024 * 1024
HASH_CHUNK_SIZE = 1024 * 1024


class InputError(Exception):
    """Invalid input or unsupported shape: exit 2."""


class ValidationFailure(Exception):
    """Content validation failure: exit 1 without writing output."""

    def __init__(self, problems):
        super().__init__("; ".join(problems))
        self.problems = list(problems)


def read_text_file(path, role):
    try:
        data = Path(path).read_bytes()
    except FileNotFoundError:
        raise InputError(role + " file missing: " + str(path))
    except OSError:
        raise InputError(role + " file unreadable: " + str(path))
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise InputError(role + " file not utf-8: " + str(path))


def read_json_file(path, role):
    try:
        return json.loads(read_text_file(path, role))
    except ValueError:
        raise InputError(role + " file not valid json: " + str(path))


def is_excluded(relative_posix):
    """True when a ./-prefixed relative path falls under an exclusion."""
    candidate = "./" + relative_posix
    return any(candidate == prefix.rstrip("/") or
               candidate.startswith(prefix) for prefix in EXCLUDE_PREFIXES)


def enumerate_corpus(root):
    """Walk the worktree and collect asset files deterministically."""
    root = Path(root)
    if not root.is_dir():
        raise InputError("repository root invalid: " + str(root))
    entries = []
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs.sort()
        for name in sorted(files):
            full = Path(current) / name
            try:
                relative = full.relative_to(root).as_posix()
            except ValueError:
                continue
            if is_excluded(relative):
                continue
            if full.suffix.lower() not in INCLUDE_EXTENSIONS:
                continue
            try:
                size = full.stat().st_size
            except OSError:
                raise InputError("asset file unreadable: " + relative)
            if size > MAX_SOURCE_BYTES:
                raise InputError("asset file too large: " + relative)
            entries.append({
                "path": relative,
                "size": size,
                "extension": full.suffix.lower(),
                "directory_class": relative.split("/", 1)[0],
            })
    entries.sort(key=lambda entry: entry["path"])
    return entries


def hash_worktree_file(root, relative):
    """SHA-256 over worktree bytes, chunked for large assets."""
    digest = hashlib.sha256()
    try:
        with open(Path(root) / relative, "rb") as handle:
            for chunk in iter(lambda: handle.read(HASH_CHUNK_SIZE), b""):
                digest.update(chunk)
    except OSError:
        raise InputError("asset file unreadable: " + relative)
    return digest.hexdigest()


def extract_item_sprite_refs(root):
    """Split every normalized item img_name on commas (M/W variants)."""
    refs = []
    for path in ITEM_FILES:
        document = read_json_file(root / path, "normalized items " + path.name)
        if not isinstance(document, list) or not document:
            raise InputError("normalized items file not non-empty array: "
                             + path.as_posix())
        for entry in document:
            if not isinstance(entry, dict) or "img_name" not in entry:
                raise InputError("normalized items entry missing img_name: "
                                 + path.as_posix())
            raw = entry["img_name"]
            if not isinstance(raw, str) or not raw:
                raise InputError("img_name not non-empty string: " + path.as_posix())
            refs.extend(part.strip() for part in raw.split(","))
    return refs


def extract_field_refs(root, path, field):
    """Collect one string field across a normalized definition array."""
    document = read_json_file(root / path, "normalized " + path.stem)
    if not isinstance(document, list) or not document:
        raise InputError("normalized file not non-empty array: " + path.as_posix())
    refs = []
    for entry in document:
        if not isinstance(entry, dict) or field not in entry:
            raise InputError("normalized entry missing " + field + ": "
                             + path.as_posix())
        value = entry[field]
        if not isinstance(value, str) or not value:
            raise InputError(field + " not non-empty string: " + path.as_posix())
        refs.append(value)
    return refs


def check_schema_type(value, allowed, label, problems):
    for kind in allowed:
        if kind == "integer" and type(value) is int:
            return
        if kind == "string" and isinstance(value, str):
            return
        if kind == "object" and isinstance(value, dict):
            return
        if kind == "array" and isinstance(value, list):
            return
        if kind == "null" and value is None:
            return
    problems.append("type mismatch at " + label + ": expected "
                    + "/".join(allowed))


def validate_against_schema(definition, schema, label):
    problems = []
    for field in schema["required"]:
        if field not in definition:
            problems.append("missing required field: " + label + "." + field)
    for field, spec in schema["properties"].items():
        if field not in definition:
            continue
        value = definition[field]
        if "const" in spec:
            if value != spec["const"]:
                problems.append("const mismatch at " + label + "." + field)
            continue
        allowed = spec.get("type")
        if isinstance(allowed, str):
            allowed = [allowed]
        if allowed:
            check_schema_type(value, allowed, label + "." + field, problems)
        if "enum" in spec and isinstance(value, str):
            if value not in spec["enum"]:
                problems.append("enum mismatch at " + label + "." + field)
        if "minimum" in spec and type(value) is int:
            if value < spec["minimum"]:
                problems.append("value below minimum at " + label + "." + field)
    if schema.get("additionalProperties") is False:
        for field in definition:
            if field not in schema["properties"]:
                problems.append("additional property: " + label + "." + field)
    return problems


def validate_digest(text, label, problems):
    if not isinstance(text, str) or len(text) != 64:
        problems.append("digest malformed at " + label)
        return
    try:
        int(text, 16)
    except ValueError:
        problems.append("digest not hexadecimal at " + label)
    if text != text.lower():
        problems.append("digest not lowercase at " + label)


def build_registry(root):
    """Enumerate and hash the corpus; validate before returning."""
    corpus = enumerate_corpus(root)
    entries = []
    for item in corpus:
        entries.append({
            "path": item["path"],
            "size": item["size"],
            "sha256": hash_worktree_file(root, item["path"]),
            "extension": item["extension"],
            "directory_class": item["directory_class"],
            "status": "registered",
        })
    problems = []
    paths = [entry["path"] for entry in entries]
    if paths != sorted(paths):
        problems.append("registry paths not in sorted order")
    if len(set(paths)) != len(paths):
        problems.append("duplicate registry paths")
    for entry in entries:
        if entry["size"] < 0:
            problems.append("negative size at " + entry["path"])
        validate_digest(entry["sha256"], entry["path"], problems)
        if is_excluded(entry["path"]):
            problems.append("excluded path leaked into registry: "
                            + entry["path"])
    if problems:
        raise ValidationFailure(problems)
    by_extension = {}
    by_directory = {}
    for entry in entries:
        by_extension[entry["extension"]] = by_extension.get(entry["extension"], 0) + 1
        by_directory[entry["directory_class"]] = \
            by_directory.get(entry["directory_class"], 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "policy": POLICY,
        "result": "success",
        "inputs": {
            "include_extensions": list(INCLUDE_EXTENSIONS),
            "exclude_prefixes": [prefix[2:] for prefix in EXCLUDE_PREFIXES],
        },
        "counts": {
            "files": len(entries),
            "bytes": sum(entry["size"] for entry in entries),
            "by_extension": by_extension,
            "by_directory_class": by_directory,
        },
        "entries": entries,
    }


def join_sprite_stems(refs, registry_paths):
    """Item/magic rule: assets/<dir>/<stem>.swf presence per ref."""
    resolved = []
    missing = []
    for ref in refs:
        if ref in registry_paths:
            resolved.append(ref)
        else:
            missing.append(ref)
    return resolved, missing


def build_coverage(root, registry):
    """Extract references, join against the registry, validate, return."""
    registry_paths = {entry["path"] for entry in registry["entries"]}
    sprite_stems = {entry["path"] for entry in registry["entries"]
                    if entry["path"].startswith("assets/sprites/")}
    magic_stems = {entry["path"] for entry in registry["entries"]
                   if entry["path"].startswith("assets/magic/")}
    sound_stems = {entry["path"] for entry in registry["entries"]
                   if entry["path"].startswith("assets/sounds/")}
    basenames = {}
    for entry in registry["entries"]:
        basenames.setdefault(entry["path"].rsplit("/", 1)[-1], []).append(entry["path"])

    item_refs = extract_item_sprite_refs(root)
    magic_refs = extract_field_refs(root, MAGICS_FILE, "img_name")
    sound_refs = extract_field_refs(root, SOUNDS_FILE, "file")
    image_refs = extract_field_refs(root, IMAGES_FILE, "path")

    item_resolved, item_missing = join_sprite_stems(
        ["assets/sprites/" + ref + ".swf" for ref in item_refs], registry_paths)
    magic_resolved, magic_missing = join_sprite_stems(
        ["assets/magic/" + ref + ".swf" for ref in magic_refs], registry_paths)
    sound_resolved, sound_missing = join_sprite_stems(
        ["assets/sounds/" + ref + ".mp3" for ref in sound_refs], registry_paths)

    image_tiers = {"basename_single": [], "basename_collision": [], "missing": []}
    for ref in image_refs:
        candidates = basenames.get(ref.rsplit("/", 1)[-1], [])
        if len(candidates) == 1:
            image_tiers["basename_single"].append(ref)
        elif candidates:
            image_tiers["basename_collision"].append(ref)
        else:
            image_tiers["missing"].append(ref)

    referenced = set(item_resolved) | set(magic_resolved) | set(sound_resolved)
    for candidates in (image_tiers["basename_single"], image_tiers["basename_collision"]):
        for ref in candidates:
            referenced.update(basenames[ref.rsplit("/", 1)[-1]])
    unreferenced = {}
    for entry in registry["entries"]:
        if entry["path"] not in referenced:
            klass = entry["directory_class"]
            unreferenced[klass] = unreferenced.get(klass, 0) + 1

    domains = {
        "item_sprites": {
            "references": len(item_refs),
            "distinct_references": len(set(item_refs)),
            "resolved": len(item_resolved),
            "missing": sorted(set(ref.rsplit("/", 1)[-1][:-len(".swf")]
                                  for ref in item_missing)),
            "rule": "assets/sprites/<stem>.swf",
        },
        "magic_sprites": {
            "references": len(magic_refs),
            "distinct_references": len(set(magic_refs)),
            "resolved": len(magic_resolved),
            "missing": sorted(set(ref.rsplit("/", 1)[-1][:-len(".swf")]
                                  for ref in magic_missing)),
            "rule": "assets/magic/<stem>.swf",
        },
        "sounds": {
            "references": len(sound_refs),
            "distinct_references": len(set(sound_refs)),
            "resolved": len(sound_resolved),
            "missing": sorted(set(ref.rsplit("/", 1)[-1][:-len(".mp3")]
                                  for ref in sound_missing)),
            "rule": "assets/sounds/<stem>.mp3",
        },
        "images": {
            "references": len(image_refs),
            "distinct_references": len(set(image_refs)),
            "resolved": len(image_tiers["basename_single"]),
            "basename_single": len(image_tiers["basename_single"]),
            "basename_collision": len(image_tiers["basename_collision"]),
            "missing": sorted(set(image_tiers["missing"])),
            "rule": "basename match (web-root-relative form preserved, never rewritten)",
        },
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "policy": POLICY,
        "result": "success",
        "inputs": {
            "normalized_files": [path.as_posix() for path in
                                 list(ITEM_FILES) + [MAGICS_FILE, SOUNDS_FILE,
                                                     IMAGES_FILE]],
        },
        "domains": domains,
        "corpus": {
            "files": registry["counts"]["files"],
            "bytes": registry["counts"]["bytes"],
        },
        "unreferenced": unreferenced,
    }


def write_outputs(out_root, registry, coverage):
    out = Path(out_root)
    (out / REGISTRY_DIR).mkdir(parents=True, exist_ok=True)
    registry_payload = (json.dumps(registry, indent=2, sort_keys=True) + "\n").encode("utf-8")
    coverage_payload = (json.dumps(coverage, indent=2, sort_keys=True) + "\n").encode("utf-8")
    (out / REGISTRY_FILE).write_bytes(registry_payload)
    (out / COVERAGE_FILE).write_bytes(coverage_payload)
    return {
        "registry": {
            "file": REGISTRY_FILE.as_posix(),
            "bytes": len(registry_payload),
            "sha256": hashlib.sha256(registry_payload).hexdigest(),
        },
        "coverage": {
            "file": COVERAGE_FILE.as_posix(),
            "bytes": len(coverage_payload),
            "sha256": hashlib.sha256(coverage_payload).hexdigest(),
        },
    }


def build_argument_parser():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--repo-root",
                        help="repository root to read (default: current directory)")
    parser.add_argument("--out-root",
                        help="registry root to write (default: same as repo root)")
    return parser


def load_loose_schema(root, filename):
    """Load a document-level schema without a kind const (registry/coverage)."""
    text = read_text_file(root / SCHEMA_DIR / filename, "schema " + filename)
    try:
        schema = json.loads(text)
    except ValueError:
        raise InputError("schema file not valid json: " + filename)
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise InputError("schema invalid, not object schema: " + filename)
    required = schema.get("required")
    properties = schema.get("properties")
    if not isinstance(required, list) or not required:
        raise InputError("schema invalid, required missing: " + filename)
    if not isinstance(properties, dict) or not properties:
        raise InputError("schema invalid, properties missing: " + filename)
    for field in required:
        if field not in properties:
            raise InputError("schema invalid, required not in properties: " + filename)
    return schema


def run_build(repo_root, out_root):
    registry = build_registry(repo_root)
    coverage = build_coverage(repo_root, registry)
    root = Path(repo_root)
    problems = []
    problems.extend(validate_against_schema(
        registry, load_loose_schema(root, REGISTRY_SCHEMA_FILE.name), "registry"))
    problems.extend(validate_against_schema(
        coverage, load_loose_schema(root, COVERAGE_SCHEMA_FILE.name), "coverage"))
    entry_schema = load_loose_schema(root, ENTRY_SCHEMA_FILE.name)
    for entry in registry["entries"]:
        problems.extend(validate_against_schema(
            entry, entry_schema, "registry_entry " + entry["path"]))
    if problems:
        raise ValidationFailure(problems)
    digests = write_outputs(out_root, registry, coverage)
    return registry, coverage, digests


def main(argv=None):
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    repo_root = args.repo_root or "."
    out_root = args.out_root or repo_root
    try:
        registry, coverage, digests = run_build(repo_root, out_root)
    except ValidationFailure as failure:
        report = {
            "schema_version": SCHEMA_VERSION,
            "policy": POLICY,
            "result": "validation-failed",
            "counts": {},
            "problems": failure.problems,
        }
        print(json.dumps(report, indent=2, sort_keys=True) + "\n", end="")
        return 1
    except InputError as error:
        print(str(error), file=sys.stderr)
        return 2
    report = {
        "schema_version": SCHEMA_VERSION,
        "policy": POLICY,
        "result": "success",
        "counts": registry["counts"],
        "domains": {name: {"references": domain.get("references"),
                           "resolved": domain.get("resolved"),
                           "missing": len(domain.get("missing", []))}
                    for name, domain in coverage["domains"].items()},
        "outputs": [digests["registry"]["file"], digests["coverage"]["file"]],
        "problems": [],
    }
    print(json.dumps(report, indent=2, sort_keys=True) + "\n", end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
