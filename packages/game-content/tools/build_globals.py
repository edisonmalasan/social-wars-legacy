"""Offline globals-tuning normalization builder and validator.

Loads the stored legacy tuning table (`globals` from `config/main.json`,
104 entries) and applies the documented patch layering (the
`atom_fusion_powerup` add of `/globals/SOUL_MIXER_POWERUPS_LEVELS`;
verified per build, items/darts-builder precedent), then keeps every
value verbatim as observed JSON with its type recorded per the
documented globals coercion ruleset (citing the field-type survey and
content census), validates key uniqueness, patch-shape conformity, and
schema-required fields including the value-type union, and diffs a
loaded-shaped re-emission against the loaded object exactly
(round-trip fidelity gate). Loaded key order is preserved; string
constants stay opaque and are never parsed as references or behavior.

On success the normalized globals package (`normalized/globals.json`,
plus the `globals` section merged into `manifest.json`) is written and
exit 0 with a JSON report on stdout is returned. Any validation failure
exits 1 without writing output. Invalid input or unsupported shapes
exit 2. Standard library only: no legacy application import, no runtime
save reads, no network, server, browser, or Flash activity.
"""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

COERCION_RULESET_VERSION = "globals-coercion-ruleset-v1"
POLICY = "globals-normalization-v1"

MAIN_CONFIG_FILE = Path("config") / "main.json"
PATCH_LIST_FILE = Path("config") / "patch" / "patches.txt"
PATCH_DIR = Path("config") / "patch"
POWERUP_PATCH = "atom_fusion_powerup"
POWERUP_PATH = "/globals/SOUL_MIXER_POWERUPS_LEVELS"
POWERUP_KEY = "SOUL_MIXER_POWERUPS_LEVELS"
MODS_LIST_FILE = Path("mods") / "mods.txt"
SCHEMA_DIR = Path("packages") / "game-content" / "schemas"
GLOBALS_SCHEMA_FILE = SCHEMA_DIR / "global_entry.schema.json"
NORMALIZED_DIR = Path("packages") / "game-content" / "normalized"
GLOBALS_FILE = NORMALIZED_DIR / "globals.json"
MANIFEST_FILE = Path("packages") / "game-content" / "manifest.json"

MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_KEYS = 64
MAX_PATCH_FILES = 32
MAX_PATCH_OPS = 4096
MAX_GLOBALS_ENTRIES = 4096

GLOBALS_KEY = "globals"
PATCHED_LAYER = "patched(atom_fusion_powerup)"


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


def apply_powerup_add(root, patch_names, stored):
    """Rule G1: apply only the powerup add of the soul-mixer schedule.

    Returns (loaded_dict, powerup_bytes). Any other globals target, a
    missing powerup patch, a divergent add shape, or a key collision
    refuses with InputError so the build stops before normalizing
    drifted content.
    """
    for name in patch_names:
        operations = load_patch_operations(root, name)
        for position, operation in enumerate(operations):
            if not isinstance(operation, dict):
                raise InputError("unsupported patch shape: " + name)
            target = operation.get("path")
            if not isinstance(target, str) or not target.startswith("/"):
                raise InputError("unsupported patch target path in " + name)
            key = target[1:].split("/", 1)[0] if len(target) > 1 else ""
            if key == GLOBALS_KEY and name != POWERUP_PATCH:
                raise InputError(
                    "patch targets globals content outside powerup in " + name
                    + " at position " + str(position) + ": " + repr(target)
                    + "; re-census required")
    if POWERUP_PATCH not in patch_names:
        raise InputError("powerup patch missing from patch order; "
                         "re-census required")
    operations = load_patch_operations(root, POWERUP_PATCH)
    if len(operations) != 1:
        raise InputError("unsupported powerup patch shape: expected exactly "
                         "one add operation")
    operation = operations[0]
    if operation.get("op") != "add" or operation.get("path") != POWERUP_PATH:
        raise InputError("unsupported powerup patch shape: expected a single "
                         "add of " + POWERUP_PATH)
    value = operation.get("value")
    if not isinstance(value, list) or not value:
        raise InputError("unsupported powerup patch shape: add value not "
                         "non-empty array")
    for position, row in enumerate(value):
        if not isinstance(row, dict):
            raise InputError("unsupported powerup patch shape: row not object "
                             "at index " + str(position))
        if set(row.keys()) != {"cash_cost", "order_increment"}:
            raise InputError("unsupported powerup patch shape: row keys drift "
                             "at index " + str(position))
        for field in ("cash_cost", "order_increment"):
            if type(row[field]) is not int or row[field] < 0:
                raise InputError("unsupported powerup patch shape: row amount "
                                 "drift at index " + str(position))
    if POWERUP_KEY in stored:
        raise InputError("powerup key collision with stored globals; "
                         "re-census required")
    powerup_bytes = read_bytes_file(root / PATCH_DIR / (POWERUP_PATCH + ".json"),
                                    "patch " + POWERUP_PATCH)
    loaded = dict(stored)
    loaded[POWERUP_KEY] = copy.deepcopy(value)
    return loaded, powerup_bytes


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


def value_type_of(value):
    """Rule G2: record the observed JSON type; bool is never integer."""
    if type(value) is int:
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, bool):
        return "boolean"
    if value is None:
        return "null"
    raise ValidationFailure(["value of unsupported JSON type: " + repr(value)[:80]])


def coerce_global(key, value, layer, label):
    """Coerce one loaded globals entry per rules G2/G3 (verbatim + typed)."""
    if not isinstance(key, str) or not key:
        raise ValidationFailure(["global key not non-empty string: " + label])
    return {
        "key": key,
        "value_type": value_type_of(value),
        "value": copy.deepcopy(value),
        "layer": layer,
    }


def build_global_definition(body, fingerprint):
    source = (MAIN_CONFIG_FILE.as_posix() if body["layer"] == "stored"
              else (PATCH_DIR / (POWERUP_PATCH + ".json")).as_posix())
    return {
        "legacy_id": body["key"],
        "kind": "global_entry",
        "source_file": source,
        "source_layer": body["layer"],
        "content_version": fingerprint,
        "key": body["key"],
        "value_type": body["value_type"],
        "value": copy.deepcopy(body["value"]),
    }


def check_schema_type(value, allowed, label, problems):
    """Enforce one JSON-Schema type union; bool never counts as integer."""
    for kind in allowed:
        if kind == "integer" and type(value) is int:
            return
        if kind == "number" and isinstance(value, (int, float)) \
                and type(value) is not bool:
            return
        if kind == "string" and isinstance(value, str):
            return
        if kind == "object" and isinstance(value, dict):
            return
        if kind == "array" and isinstance(value, list):
            return
        if kind == "boolean" and type(value) is bool:
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
        if "enum" in spec:
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
    # Cross-check the recorded type against the servant value union.
    if definition.get("value_type") == "integer" and \
            type(definition.get("value")) is not int:
        problems.append("value_type/value mismatch at " + label)
    return problems


def check_round_trip(definitions, loaded_keys, loaded):
    """Diff legacy re-emission against the loaded object exactly."""
    problems = []
    if [item["legacy_id"] for item in definitions] != loaded_keys:
        problems.append("round-trip globals key order mismatch")
    for definition, key in zip(definitions, loaded_keys):
        entry_label = "round-trip global " + definition["legacy_id"]
        if key not in loaded:
            problems.append(entry_label + ": loaded key missing")
            continue
        original = loaded[key]
        try:
            body = coerce_global(key, original,
                                 definition["source_layer"], "round-trip")
        except ValidationFailure as failure:
            problems.extend([entry_label + ": " + item for item in failure.problems])
            continue
        if body["value_type"] != definition["value_type"]:
            problems.append(entry_label + ": drift at value_type")
        if body["value"] != definition["value"]:
            problems.append(entry_label + ": drift at value")
        if type(body["value"]) is not type(definition["value"]) and not (
                isinstance(body["value"], float) and isinstance(definition["value"], float)):
            # bool/int distinction matters; floats compare by = above but
            # integral floats must never silently become ints.
            if not (type(body["value"]) is int and type(definition["value"]) is int):
                problems.append(entry_label + ": type drift at value")
        if body["layer"] != definition["source_layer"]:
            problems.append(entry_label + ": drift at source_layer")
    return problems


def load_all(root):
    """Load stored globals with patch layering, drift, and mod guards."""
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
    if GLOBALS_KEY not in document or not isinstance(document[GLOBALS_KEY], dict):
        raise InputError("unsupported content shape: globals not object")
    if not document[GLOBALS_KEY] or len(document[GLOBALS_KEY]) > MAX_GLOBALS_ENTRIES:
        raise InputError("globals entry limit exceeded")
    patch_names = parse_patch_list(
        read_text_file(root / PATCH_LIST_FILE, "patch list"))
    mods_text = read_text_file(root / MODS_LIST_FILE, "mods list")
    active_mods, inactive_mods = parse_mods_list(mods_text)
    if active_mods:
        raise InputError("active mods unsupported, re-census required: "
                         + ", ".join(active_mods))
    stored = document[GLOBALS_KEY]
    loaded, powerup_bytes = apply_powerup_add(root, patch_names, stored)
    mods_bytes = read_bytes_file(root / MODS_LIST_FILE, "mods list")
    manifest_text = read_text_file(root / MANIFEST_FILE, "package manifest")
    try:
        manifest_document = json.loads(manifest_text)
    except ValueError:
        raise InputError("package manifest not valid json")
    if not isinstance(manifest_document, dict):
        raise InputError("package manifest not object")
    return {
        "stored_globals": stored,
        "loaded_globals": loaded,
        "loaded_keys": list(loaded.keys()),
        "patch_names": patch_names,
        "active_mods": active_mods,
        "inactive_mods": inactive_mods,
        "manifest": manifest_document,
        "main_bytes": main_bytes,
        "powerup_bytes": powerup_bytes,
        "mods_bytes": mods_bytes,
    }


def fingerprint_inputs(layers):
    digest = hashlib.sha256()
    digest.update(layers["main_bytes"])
    digest.update(layers["powerup_bytes"])
    digest.update(layers["mods_bytes"])
    return digest.hexdigest()


def build_package(repo_root, out_root):
    """Build in memory, validate everything, then write output files."""
    root = Path(repo_root)
    layers = load_all(root)
    fingerprint = fingerprint_inputs(layers)
    stored = layers["stored_globals"]
    loaded = layers["loaded_globals"]
    loaded_keys = layers["loaded_keys"]
    problems = []
    bodies = []
    for key in loaded_keys:
        layer = PATCHED_LAYER if key == POWERUP_KEY else "stored"
        try:
            bodies.append(coerce_global(key, loaded[key], layer,
                                        "global key " + key))
        except ValidationFailure as failure:
            problems.extend(failure.problems)
    if problems:
        raise ValidationFailure(problems)
    if len(set(loaded_keys)) != len(loaded_keys):
        raise ValidationFailure(["duplicate globals legacy_id"])
    if POWERUP_KEY not in loaded:
        raise ValidationFailure(["powerup schedule missing from loaded globals"])
    definitions = [build_global_definition(body, fingerprint) for body in bodies]
    for item in definitions:
        if item["legacy_id"] != item["key"]:
            problems.append("legacy_id/key drift at " + item["legacy_id"])
    if problems:
        raise ValidationFailure(problems)
    globals_schema = load_schema(root, GLOBALS_SCHEMA_FILE.name, "global_entry")
    for item in definitions:
        problems.extend(validate_against_schema(
            item, globals_schema, "global_entry " + item["legacy_id"]))
    if problems:
        raise ValidationFailure(problems)
    round_problems = check_round_trip(definitions, loaded_keys, loaded)
    if round_problems:
        raise ValidationFailure(round_problems)
    type_counts = {}
    for item in definitions:
        type_counts[item["value_type"]] = type_counts.get(item["value_type"], 0) + 1
    string_keys = sorted(item["legacy_id"] for item in definitions
                         if item["value_type"] == "string")
    files = {GLOBALS_FILE: definitions}
    globals_section = {
        "schema_version": 1,
        "policy": POLICY,
        "result": "success",
        "inputs": {
            "main": {
                "file": MAIN_CONFIG_FILE.as_posix(),
                "bytes": len(layers["main_bytes"]),
                "sha256": hashlib.sha256(layers["main_bytes"]).hexdigest(),
            },
            "powerup_patch": {
                "file": (PATCH_DIR / (POWERUP_PATCH + ".json")).as_posix(),
                "bytes": len(layers["powerup_bytes"]),
                "sha256": hashlib.sha256(layers["powerup_bytes"]).hexdigest(),
            },
            "mods": {
                "status": "inactive",
                "active_mods": layers["active_mods"],
                "inactive_mods": layers["inactive_mods"],
            },
            "patch_order": layers["patch_names"],
            "globals_layering": "add",
        },
        "coercion_ruleset": COERCION_RULESET_VERSION,
        "content_fingerprint": fingerprint,
        "counts": {
            "stored_globals": len(stored),
            "loaded_globals": len(loaded),
            "globals": len(definitions),
            "value_types": type_counts,
            "string_keys": string_keys,
        },
        "validation": {
            "duplicate_ids": 0,
            "amount_violations": 0,
            "missing_fields": 0,
            "round_trip_diffs": 0,
        },
        "outputs": [],
        "notes": [
            "Stored globals map one-to-one to definitions plus the single "
            "powerup add; legacy_id is the constant name in loaded key "
            "order, never re-sorted (rules G1/G3).",
            "Values are verbatim observed JSON with recorded types; "
            "integers, floats, strings, arrays, objects, booleans, and "
            "null each round-trip exactly (rule G2).",
            "String constants (version lists, URL, date, depot-limits "
            "string, friend-reward CSV strings) stay opaque display and "
            "config data, never parsed as references or behavior.",
            "No other patch targets globals; the build refuses patch "
            "drift and active mods explicitly.",
        ],
    }
    payloads = {}
    for path, entries in files.items():
        payloads[path] = json.dumps(entries, indent=2) + "\n"
    return globals_section, payloads


def write_outputs(out_root, globals_section, payloads):
    # Byte-exact writes: payloads are encoded once and the same bytes feed
    # the digest records. The globals section is merged into the existing
    # package manifest (prior keys preserved); the manifest cannot digest
    # itself, so only the normalized globals file is digested.
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
    globals_section["outputs"] = outputs
    manifest_path = out / MANIFEST_FILE
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise InputError("package manifest not object")
    manifest["globals"] = globals_section
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
    globals_section, payloads = build_package(repo_root, out_root)
    manifest = write_outputs(out_root, globals_section, payloads)
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
        "counts": manifest["globals"]["counts"],
        "outputs": [entry["file"] for entry in manifest["globals"]["outputs"]],
        "problems": [],
    }
    print(json.dumps(report, indent=2, sort_keys=True) + "\n", end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
