"""Offline images normalization builder and validator.

Loads the stored legacy asset-path index (`images` from `config/main.json`,
607 entries, every value the locale string `en`) directly with no patch
layering (no active patch targets the key; verified per build), preserves
every path verbatim with a recorded locale per the documented images
coercion ruleset (citing the field-type survey), validates key
uniqueness and non-emptiness, locale exactly `en`, and schema-required
fields, and diffs a legacy-shaped re-emission against the stored object
exactly (round-trip fidelity gate). Stored document order is preserved;
paths are recorded references only, never checked against disk and never
executed (asset truth and conversion belong to M4).

On success the normalized images package (`normalized/images.json`,
plus the `images` section merged into `manifest.json`) is written and
exit 0 with a JSON report on stdout is returned. Any validation failure
exits 1 without writing output. Invalid input or unsupported shapes
exit 2. Standard library only: no legacy application import, no runtime
save reads, no filesystem stat calls, no network, server, browser, or
Flash activity.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys

COERCION_RULESET_VERSION = "images-coercion-ruleset-v1"
POLICY = "images-normalization-v1"

MAIN_CONFIG_FILE = Path("config") / "main.json"
PATCH_LIST_FILE = Path("config") / "patch" / "patches.txt"
PATCH_DIR = Path("config") / "patch"
MODS_LIST_FILE = Path("mods") / "mods.txt"
SCHEMA_DIR = Path("packages") / "game-content" / "schemas"
IMAGES_SCHEMA_FILE = SCHEMA_DIR / "image_asset.schema.json"
NORMALIZED_DIR = Path("packages") / "game-content" / "normalized"
IMAGES_FILE = NORMALIZED_DIR / "images.json"
MANIFEST_FILE = Path("packages") / "game-content" / "manifest.json"

MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_KEYS = 64
MAX_PATCH_FILES = 32
MAX_PATCH_OPS = 4096
MAX_IMAGES_ENTRIES = 4096

IMAGES_KEY = "images"
EXPECTED_LOCALE = "en"


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
    if len(data) > MAX_SOURCE_BYTES:
        raise InputError(role + " file too large: " + str(path))
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise InputError(role + " file not utf-8: " + str(path))


def read_bytes_file(path, role):
    try:
        data = Path(path).read_bytes()
    except FileNotFoundError:
        raise InputError(role + " file missing: " + str(path))
    except OSError:
        raise InputError(role + " file unreadable: " + str(path))
    if len(data) > MAX_SOURCE_BYTES:
        raise InputError(role + " file too large: " + str(path))
    return data


def parse_patch_list(text):
    """Return the ordered active patch names, mirroring the legacy loader."""
    names = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.endswith(".json"):
            stripped = stripped[:-len(".json")]
        if not stripped:
            raise InputError("unsupported patch list shape: empty patch name")
        names.append(stripped)
    if not names:
        raise InputError("unsupported patch list shape: no active patches")
    if len(names) > MAX_PATCH_FILES:
        raise InputError("patch limit exceeded")
    if len(set(names)) != len(names):
        raise InputError("unsupported patch list shape: duplicate patch name")
    return names


def parse_mods_list(text):
    """Return (active_mods, inactive_mods), mirroring the legacy loader."""
    active = []
    inactive = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            token = stripped[1:].strip()
            if token and not any(char.isspace() for char in token):
                if token.endswith(".json"):
                    token = token[:-len(".json")]
                inactive.append(token)
            continue
        name = stripped[:-len(".json")] if stripped.endswith(".json") else stripped
        if not name:
            raise InputError("unsupported mods list shape: empty mod name")
        active.append(name)
    if len(set(active)) != len(active):
        raise InputError("unsupported mods list shape: duplicate mod name")
    return active, inactive


def load_patch_operations(root, name):
    text = read_text_file(root / PATCH_DIR / (name + ".json"), "patch " + name)
    try:
        operations = json.loads(text)
    except ValueError:
        raise InputError("patch file not valid json: " + name)
    if not isinstance(operations, list) or not operations:
        raise InputError("unsupported patch shape: " + name)
    if len(operations) > MAX_PATCH_OPS:
        raise InputError("patch operation limit exceeded: " + name)
    return operations


def check_no_images_patch_targets(root, patch_names):
    """Refuse patch drift: no patch may target images."""
    for name in patch_names:
        operations = load_patch_operations(root, name)
        for position, operation in enumerate(operations):
            if not isinstance(operation, dict):
                raise InputError("unsupported patch shape: " + name)
            target = operation.get("path")
            if not isinstance(target, str) or not target.startswith("/"):
                raise InputError("unsupported patch target path in " + name)
            key = target[1:].split("/", 1)[0] if len(target) > 1 else ""
            if key == IMAGES_KEY:
                raise InputError(
                    "patch targets images content in " + name
                    + " at position " + str(position) + ": " + repr(target)
                    + "; re-census required")


def load_schema(root, filename, kind):
    text = read_text_file(root / SCHEMA_DIR / filename, "schema " + kind)
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
    kind_spec = properties.get("kind")
    if not isinstance(kind_spec, dict) or kind_spec.get("const") != kind:
        raise InputError("schema invalid, kind const mismatch: " + filename)
    return schema


def coerce_image(path, locale, label):
    """Coerce one stored images entry per rules M1/M2 (verbatim + en)."""
    if not isinstance(path, str) or not path:
        raise ValidationFailure(["image path not non-empty string: " + label])
    if locale != EXPECTED_LOCALE:
        raise ValidationFailure(["image locale drift at " + label + ": "
                                 + repr(locale)])
    return {"path": path, "locale": locale}


def build_image_definition(body, fingerprint):
    return {
        "legacy_id": body["path"],
        "kind": "image_asset",
        "source_file": MAIN_CONFIG_FILE.as_posix(),
        "source_layer": "stored",
        "content_version": fingerprint,
        "path": body["path"],
        "locale": body["locale"],
    }


def check_schema_type(value, allowed, label, problems):
    """Enforce one JSON-Schema type union; bool never counts as integer."""
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
    """Enforce schema required/type/const/enum/minimum/minItems/items/
    additionalProperties gates."""
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
        if "minItems" in spec and isinstance(value, list):
            if len(value) < spec["minItems"]:
                problems.append("array below minItems at " + label + "." + field)
        items_spec = spec.get("items")
        if isinstance(value, list) and isinstance(items_spec, dict):
            item_types = items_spec.get("type")
            if isinstance(item_types, str):
                item_types = [item_types]
            if item_types:
                for index, element in enumerate(value):
                    sub = []
                    check_schema_type(element, item_types,
                                      label + "." + field + "[" + str(index) + "]",
                                      sub)
                    problems.extend(sub)
    if schema.get("additionalProperties") is False:
        for field in definition:
            if field not in schema["properties"]:
                problems.append("additional property: " + label + "." + field)
    return problems


def extension_of(path):
    """Record the file extension class for manifest statistics."""
    if "." not in path:
        return "(none)"
    return path.rsplit(".", 1)[-1].lower()


def check_round_trip(definitions, ordered_paths, stored):
    """Diff legacy re-emission against the stored object exactly."""
    problems = []
    if [item["legacy_id"] for item in definitions] != ordered_paths:
        problems.append("round-trip images key order mismatch")
    for definition, path in zip(definitions, ordered_paths):
        entry_label = "round-trip image " + definition["legacy_id"]
        original = stored.get(path)
        if original != EXPECTED_LOCALE:
            problems.append(entry_label + ": stored value not en")
            continue
        try:
            body = coerce_image(path, original, "round-trip")
        except ValidationFailure as failure:
            problems.extend([entry_label + ": " + item for item in failure.problems])
            continue
        if body["path"] != definition["path"]:
            problems.append(entry_label + ": drift at path")
        if body["locale"] != definition["locale"]:
            problems.append(entry_label + ": drift at locale")
    return problems


def load_all(root):
    """Load the stored images object with patch-drift and mod guards."""
    root = Path(root)
    if not root.is_dir():
        raise InputError("repository root invalid: " + str(root))
    main_bytes = read_bytes_file(root / MAIN_CONFIG_FILE, "content")
    try:
        document = json.loads(main_bytes.decode("utf-8"))
    except ValueError:
        raise InputError("content file not valid json")
    if not isinstance(document, dict) or not document:
        raise InputError("unsupported content shape: top level not object")
    if len(document) > MAX_TOTAL_KEYS:
        raise InputError("content key limit exceeded")
    if IMAGES_KEY not in document or not isinstance(document[IMAGES_KEY], dict):
        raise InputError("unsupported content shape: images not object")
    if not document[IMAGES_KEY] or len(document[IMAGES_KEY]) > MAX_IMAGES_ENTRIES:
        raise InputError("images entry limit exceeded")
    patch_names = parse_patch_list(
        read_text_file(root / PATCH_LIST_FILE, "patch list"))
    mods_text = read_text_file(root / MODS_LIST_FILE, "mods list")
    active_mods, inactive_mods = parse_mods_list(mods_text)
    if active_mods:
        raise InputError("active mods unsupported, re-census required: "
                         + ", ".join(active_mods))
    check_no_images_patch_targets(root, patch_names)
    mods_bytes = read_bytes_file(root / MODS_LIST_FILE, "mods list")
    manifest_text = read_text_file(root / MANIFEST_FILE, "package manifest")
    try:
        manifest_document = json.loads(manifest_text)
    except ValueError:
        raise InputError("package manifest not valid json")
    if not isinstance(manifest_document, dict):
        raise InputError("package manifest not object")
    return {
        "images": document[IMAGES_KEY],
        "patch_names": patch_names,
        "active_mods": active_mods,
        "inactive_mods": inactive_mods,
        "manifest": manifest_document,
        "main_bytes": main_bytes,
        "mods_bytes": mods_bytes,
    }


def fingerprint_inputs(layers):
    digest = hashlib.sha256()
    digest.update(layers["main_bytes"])
    digest.update(layers["mods_bytes"])
    return digest.hexdigest()


def build_package(repo_root, out_root):
    """Build in memory, validate everything, then write output files."""
    root = Path(repo_root)
    layers = load_all(root)
    fingerprint = fingerprint_inputs(layers)
    stored = layers["images"]
    ordered_paths = list(stored.keys())
    problems = []
    bodies = []
    for path in ordered_paths:
        try:
            bodies.append(coerce_image(path, stored[path], "image " + path))
        except ValidationFailure as failure:
            problems.extend(failure.problems)
    if problems:
        raise ValidationFailure(problems)
    if len(set(ordered_paths)) != len(ordered_paths):
        raise ValidationFailure(["duplicate images legacy_id"])
    definitions = [build_image_definition(body, fingerprint) for body in bodies]
    images_schema = load_schema(root, IMAGES_SCHEMA_FILE.name, "image_asset")
    for item in definitions:
        problems.extend(validate_against_schema(
            item, images_schema, "image_asset " + item["legacy_id"]))
    if problems:
        raise ValidationFailure(problems)
    round_problems = check_round_trip(definitions, ordered_paths, stored)
    if round_problems:
        raise ValidationFailure(round_problems)
    extensions = {}
    for path in ordered_paths:
        extension = extension_of(path)
        extensions[extension] = extensions.get(extension, 0) + 1
    leading_slash = sum(1 for path in ordered_paths if path.startswith("/"))
    swf_paths = sorted(path for path in ordered_paths
                       if extension_of(path) == "swf")
    files = {IMAGES_FILE: definitions}
    images_section = {
        "schema_version": 1,
        "policy": POLICY,
        "result": "success",
        "inputs": {
            "main": {
                "file": MAIN_CONFIG_FILE.as_posix(),
                "bytes": len(layers["main_bytes"]),
                "sha256": hashlib.sha256(layers["main_bytes"]).hexdigest(),
            },
            "mods": {
                "status": "inactive",
                "active_mods": layers["active_mods"],
                "inactive_mods": layers["inactive_mods"],
            },
            "patch_order": layers["patch_names"],
            "images_patch_targets": "none",
        },
        "coercion_ruleset": COERCION_RULESET_VERSION,
        "content_fingerprint": fingerprint,
        "counts": {
            "stored_images": len(stored),
            "images": len(definitions),
            "extensions": extensions,
            "leading_slash": leading_slash,
            "swf_paths": swf_paths,
        },
        "validation": {
            "duplicate_ids": 0,
            "amount_violations": 0,
            "missing_fields": 0,
            "round_trip_diffs": 0,
        },
        "outputs": [],
        "notes": [
            "Stored images map one-to-one to definitions; legacy_id is "
            "the asset path verbatim in stored document order, never "
            "rewritten (rule M2).",
            "Every locale is exactly en; anything else fails as drift "
            "(rule M1).",
            "Extension distribution and leading-slash counts are "
            "recorded without enforcement.",
            "Swf paths are archival references for the M4 asset "
            "pipeline; they are never executed, converted, or checked "
            "against disk here.",
            "No active patch targets images; the build refuses patch "
            "drift and active mods explicitly.",
        ],
    }
    payloads = {}
    for path, entries in files.items():
        payloads[path] = json.dumps(entries, indent=2) + "\n"
    return images_section, payloads


def write_outputs(out_root, images_section, payloads):
    # Byte-exact writes: payloads are encoded once and the same bytes feed
    # the digest records. The images section is merged into the existing
    # package manifest (prior keys preserved); the manifest cannot digest
    # itself, so only the normalized images file is digested.
    out = Path(out_root)
    (out / NORMALIZED_DIR).mkdir(parents=True, exist_ok=True)
    outputs = []
    for path, payload in payloads.items():
        data = payload.encode("utf-8")
        (out / path).write_bytes(data)
        outputs.append({
            "file": path.as_posix(),
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    images_section["outputs"] = outputs
    manifest_path = out / MANIFEST_FILE
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise InputError("package manifest not object")
    manifest["images"] = images_section
    manifest_path.write_bytes(
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return manifest


def build_argument_parser():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--repo-root",
                        help="repository root to read (default: current directory)")
    parser.add_argument("--out-root",
                        help="package root to write (default: same as repo root)")
    return parser


def run_build(repo_root, out_root):
    images_section, payloads = build_package(repo_root, out_root)
    manifest = write_outputs(out_root, images_section, payloads)
    return manifest


def main(argv=None):
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    repo_root = args.repo_root or "."
    out_root = args.out_root or repo_root
    try:
        manifest = run_build(repo_root, out_root)
    except ValidationFailure as failure:
        report = {
            "schema_version": 1,
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
        "schema_version": 1,
        "policy": POLICY,
        "result": "success",
        "counts": manifest["images"]["counts"],
        "outputs": [entry["file"] for entry in manifest["images"]["outputs"]],
        "problems": [],
    }
    print(json.dumps(report, indent=2, sort_keys=True) + "\n", end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
