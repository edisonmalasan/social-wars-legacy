"""Offline darts-schedule normalization builder and validator.

Loads the stored legacy darts table (`darts_items` from `config/main.json`,
30 entries) and applies the documented patch layering (the `targets`
whole-array replace of `/darts_items`, 27 entries; verified per build,
items-builder precedent), then keeps every pooled integer and
`start_date` string verbatim per the documented darts coercion ruleset
(citing the field-type survey and content census), validates id
uniqueness, pooled/extra references against the committed normalized
items legacy-ID set (the quest-precedent cross-domain edge), and
schema-required fields, and diffs a patched-shaped re-emission against
the patched array exactly (round-trip fidelity gate). Patched order is
preserved; `start_date` values are derivation inputs only:
`make_dynamic` never runs and served bytes stay out of scope exactly as
in the content census.

On success the normalized darts package (`normalized/darts_items.json`,
plus the `darts` section merged into `manifest.json`) is written and
exit 0 with a JSON report on stdout is returned. Any validation failure
exits 1 without writing output. Invalid input or unsupported shapes
exit 2. Standard library only: no legacy application import, no runtime
save reads, no network, server, browser, Flash, or wall-clock activity.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys

COERCION_RULESET_VERSION = "darts-coercion-ruleset-v1"
POLICY = "darts-normalization-v1"

MAIN_CONFIG_FILE = Path("config") / "main.json"
PATCH_LIST_FILE = Path("config") / "patch" / "patches.txt"
PATCH_DIR = Path("config") / "patch"
TARGETS_PATCH = "targets"
MODS_LIST_FILE = Path("mods") / "mods.txt"
SCHEMA_DIR = Path("packages") / "game-content" / "schemas"
DARTS_SCHEMA_FILE = SCHEMA_DIR / "darts_item.schema.json"
NORMALIZED_DIR = Path("packages") / "game-content" / "normalized"
BUILDINGS_FILE = NORMALIZED_DIR / "buildings.json"
UNITS_FILE = NORMALIZED_DIR / "units.json"
SPECIALS_FILE = NORMALIZED_DIR / "specials.json"
DARTS_FILE = NORMALIZED_DIR / "darts_items.json"
MANIFEST_FILE = Path("packages") / "game-content" / "manifest.json"

MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_KEYS = 64
MAX_PATCH_FILES = 32
MAX_PATCH_OPS = 4096
MAX_DARTS_ENTRIES = 4096

# Patched darts field set (field-type survey: mixed with native id and
# extra_item, an items id array, and a start_date datetime string).
# Anything else is content drift.
DARTS_FIELDS = ("id", "start_date", "items", "extra_item")

DARTS_KEY = "darts_items"


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


def apply_targets_replace(root, patch_names):
    """Rule D1: apply only the targets whole-array replace of /darts_items.

    Returns (patched_entries, targets_bytes). Any other darts target, a
    missing targets patch, or a divergent replace shape refuses with
    InputError so the build stops before normalizing drifted content.
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
            if key == DARTS_KEY and name != TARGETS_PATCH:
                raise InputError(
                    "patch targets darts content outside targets in " + name
                    + " at position " + str(position) + ": " + repr(target)
                    + "; re-census required")
    if TARGETS_PATCH not in patch_names:
        raise InputError("targets patch missing from patch order; "
                         "re-census required")
    operations = load_patch_operations(root, TARGETS_PATCH)
    if len(operations) != 1:
        raise InputError("unsupported targets patch shape: expected exactly "
                         "one replace operation")
    operation = operations[0]
    if operation.get("op") != "replace" or operation.get("path") != "/darts_items":
        raise InputError("unsupported targets patch shape: expected a single "
                         "replace of /darts_items")
    value = operation.get("value")
    if not isinstance(value, list) or not value:
        raise InputError("unsupported targets patch shape: replace value not "
                         "non-empty array")
    if len(value) > MAX_DARTS_ENTRIES:
        raise InputError("darts entry limit exceeded in targets patch")
    targets_bytes = read_bytes_file(root / PATCH_DIR / (TARGETS_PATCH + ".json"),
                                    "patch " + TARGETS_PATCH)
    return value, targets_bytes


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


def load_items_id_set(root):
    """Read the committed normalized items outputs for the reference edge."""
    union = set()
    counts = {}
    for path in (BUILDINGS_FILE, UNITS_FILE, SPECIALS_FILE):
        text = read_text_file(root / path, "normalized items " + path.name)
        try:
            entries = json.loads(text)
        except ValueError:
            raise InputError("normalized items file not valid json: "
                             + path.as_posix())
        if not isinstance(entries, list) or not entries:
            raise InputError("normalized items file not non-empty array: "
                             + path.as_posix())
        for entry in entries:
            if not isinstance(entry, dict):
                raise InputError("normalized items entry not object: "
                                 + path.as_posix())
            legacy_id = entry.get("legacy_id")
            if not isinstance(legacy_id, str) or not legacy_id:
                raise InputError("normalized items entry missing legacy_id: "
                                 + path.as_posix())
            union.add(legacy_id)
        counts[path.stem] = len(entries)
    if len(union) != sum(counts.values()):
        raise InputError("normalized items legacy_id overlap across outputs")
    return union, counts


def coerce_darts(raw, label):
    """Coerce one patched darts_items entry per rules D2/D3 (verbatim)."""
    if not isinstance(raw, dict):
        raise ValidationFailure(["entry not object: " + label])
    problems = []
    for field in DARTS_FIELDS:
        if field not in raw:
            problems.append("missing field: " + label + "." + field)
    for field in raw:
        if field not in DARTS_FIELDS:
            problems.append("unexpected field: " + label + "." + field)
    if problems:
        raise ValidationFailure(problems)
    if type(raw["id"]) is not int:
        raise ValidationFailure(["darts id not native integer: " + label])
    if not isinstance(raw["start_date"], str) or not raw["start_date"]:
        raise ValidationFailure(["start_date not non-empty string: " + label])
    items = raw["items"]
    if not isinstance(items, list) or not items:
        raise ValidationFailure(["items not non-empty array: " + label])
    for value in items:
        if type(value) is not int:
            raise ValidationFailure(["items element not integer: " + label])
    if type(raw["extra_item"]) is not int:
        raise ValidationFailure(["extra_item not native integer: " + label])
    return {
        "id": raw["id"],
        "start_date": raw["start_date"],
        "items": list(items),
        "item_refs": [str(value) for value in items],
        "extra_item": raw["extra_item"],
        "extra_ref": str(raw["extra_item"]),
    }


def build_darts_definition(body, fingerprint):
    return {
        "legacy_id": str(body["id"]),
        "kind": "darts_item",
        "source_file": (PATCH_DIR / (TARGETS_PATCH + ".json")).as_posix(),
        "source_layer": "patched(targets)",
        "content_version": fingerprint,
        "id": body["id"],
        "start_date": body["start_date"],
        "items": list(body["items"]),
        "item_refs": list(body["item_refs"]),
        "extra_item": body["extra_item"],
        "extra_ref": body["extra_ref"],
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


def validate_darts_references(darts, items_id_set):
    """Rule D2: every pooled and extra id must resolve to an item."""
    problems = []
    for definition in darts:
        for key in definition["item_refs"]:
            if key not in items_id_set:
                problems.append("unresolvable darts pool reference: "
                                + definition["legacy_id"] + " -> " + key)
        if definition["extra_ref"] not in items_id_set:
            problems.append("unresolvable darts extra reference: "
                            + definition["legacy_id"] + " -> "
                            + definition["extra_ref"])
        if definition["item_refs"] != [str(value) for value in definition["items"]]:
            problems.append("item_refs drift at darts "
                            + definition["legacy_id"])
        if definition["extra_ref"] != str(definition["extra_item"]):
            problems.append("extra_ref drift at darts "
                            + definition["legacy_id"])
    return problems


def check_round_trip(darts, patched):
    """Diff legacy re-emission against the patched array exactly."""
    problems = []
    if len(darts) != len(patched):
        problems.append("round-trip darts count mismatch: %d definitions vs %d patched"
                        % (len(darts), len(patched)))
        return problems
    for definition, original in zip(darts, patched):
        entry_label = "round-trip darts " + definition["legacy_id"]
        if not isinstance(original, dict):
            problems.append(entry_label + ": patched entry not object")
            continue
        if str(original.get("id")) != definition["legacy_id"]:
            problems.append(entry_label + ": order/identity mismatch")
            continue
        try:
            body = coerce_darts(original, "round-trip")
        except ValidationFailure as failure:
            problems.extend([entry_label + ": " + item for item in failure.problems])
            continue
        for field in ("id", "start_date", "items", "extra_item"):
            if body[field] != definition[field]:
                problems.append(entry_label + ": drift at " + field)
        if body["item_refs"] != definition["item_refs"]:
            problems.append(entry_label + ": drift at item_refs")
        if body["extra_ref"] != definition["extra_ref"]:
            problems.append(entry_label + ": drift at extra_ref")
        if set(original.keys()) != set(DARTS_FIELDS):
            problems.append(entry_label + ": field-set drift "
                            + repr(sorted(set(original.keys()) ^ set(DARTS_FIELDS))))
    return problems


def load_all(root):
    """Load stored darts with patch layering, drift, and mod guards."""
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
    if DARTS_KEY not in document or not isinstance(document[DARTS_KEY], list):
        raise InputError("unsupported content shape: darts_items not array")
    patch_names = parse_patch_list(
        read_text_file(root / PATCH_LIST_FILE, "patch list"))
    mods_text = read_text_file(root / MODS_LIST_FILE, "mods list")
    active_mods, inactive_mods = parse_mods_list(mods_text)
    if active_mods:
        raise InputError("active mods unsupported, re-census required: "
                         + ", ".join(active_mods))
    patched, targets_bytes = apply_targets_replace(root, patch_names)
    items_id_set, items_counts = load_items_id_set(root)
    mods_bytes = read_bytes_file(root / MODS_LIST_FILE, "mods list")
    manifest_text = read_text_file(root / MANIFEST_FILE, "package manifest")
    try:
        manifest_document = json.loads(manifest_text)
    except ValueError:
        raise InputError("package manifest not valid json")
    if not isinstance(manifest_document, dict):
        raise InputError("package manifest not object")
    return {
        "stored_darts": document[DARTS_KEY],
        "patched_darts": patched,
        "patch_names": patch_names,
        "active_mods": active_mods,
        "inactive_mods": inactive_mods,
        "items_id_set": items_id_set,
        "items_counts": items_counts,
        "manifest": manifest_document,
        "main_bytes": main_bytes,
        "targets_bytes": targets_bytes,
        "mods_bytes": mods_bytes,
    }


def fingerprint_inputs(layers):
    digest = hashlib.sha256()
    digest.update(layers["main_bytes"])
    digest.update(layers["targets_bytes"])
    digest.update(layers["mods_bytes"])
    return digest.hexdigest()


def build_package(repo_root, out_root):
    """Build in memory, validate everything, then write output files."""
    root = Path(repo_root)
    layers = load_all(root)
    fingerprint = fingerprint_inputs(layers)
    stored = layers["stored_darts"]
    patched = layers["patched_darts"]
    problems = []
    bodies = []
    for entry in patched:
        label = ("darts id " + repr(entry.get("id"))
                 if isinstance(entry, dict) else "darts entry")
        try:
            bodies.append(coerce_darts(entry, label))
        except ValidationFailure as failure:
            problems.extend(failure.problems)
    if problems:
        raise ValidationFailure(problems)
    darts = [build_darts_definition(body, fingerprint) for body in bodies]
    if len({item["legacy_id"] for item in darts}) != len(darts):
        raise ValidationFailure(["duplicate darts legacy_id in patched darts_items"])
    problems.extend(validate_darts_references(darts, layers["items_id_set"]))
    if problems:
        raise ValidationFailure(problems)
    darts_schema = load_schema(root, DARTS_SCHEMA_FILE.name, "darts_item")
    for item in darts:
        problems.extend(validate_against_schema(
            item, darts_schema, "darts_item " + item["legacy_id"]))
    if problems:
        raise ValidationFailure(problems)
    round_problems = check_round_trip(darts, patched)
    if round_problems:
        raise ValidationFailure(round_problems)
    pool_sizes = sorted({len(item["items"]) for item in darts})
    files = {DARTS_FILE: darts}
    darts_section = {
        "schema_version": 1,
        "policy": POLICY,
        "result": "success",
        "inputs": {
            "main": {
                "file": MAIN_CONFIG_FILE.as_posix(),
                "bytes": len(layers["main_bytes"]),
                "sha256": hashlib.sha256(layers["main_bytes"]).hexdigest(),
            },
            "targets_patch": {
                "file": (PATCH_DIR / (TARGETS_PATCH + ".json")).as_posix(),
                "bytes": len(layers["targets_bytes"]),
                "sha256": hashlib.sha256(layers["targets_bytes"]).hexdigest(),
            },
            "mods": {
                "status": "inactive",
                "active_mods": layers["active_mods"],
                "inactive_mods": layers["inactive_mods"],
            },
            "patch_order": layers["patch_names"],
            "darts_layering": "replace",
            "items_reference_edge": {
                "files": [
                    BUILDINGS_FILE.as_posix(),
                    UNITS_FILE.as_posix(),
                    SPECIALS_FILE.as_posix(),
                ],
                "counts": dict(layers["items_counts"]),
                "union_legacy_ids": len(layers["items_id_set"]),
            },
        },
        "coercion_ruleset": COERCION_RULESET_VERSION,
        "content_fingerprint": fingerprint,
        "counts": {
            "stored_darts": len(stored),
            "patched_darts": len(patched),
            "darts": len(darts),
            "pool_sizes": pool_sizes,
        },
        "validation": {
            "duplicate_ids": 0,
            "amount_violations": 0,
            "missing_fields": 0,
            "round_trip_diffs": 0,
            "unresolvable_references": 0,
        },
        "outputs": [],
        "notes": [
            "Stored darts are replace inputs only; the targets patch "
            "replaces the whole array and only the patched entries are "
            "normalized (rule D1).",
            "Only the single targets replace of /darts_items is applied; "
            "any other darts target or divergent replace shape refuses "
            "the build until re-censused.",
            "Pooled and extra ids resolve against the normalized items "
            "legacy-ID set with references carried in stored pool order "
            "(rule D2).",
            "start_date values are stored derivation inputs for "
            "make_dynamic, preserved verbatim and never recomputed; "
            "served bytes drift with the wall clock and are explicitly "
            "out of scope (rule D3).",
            "No active patch beyond the ordered list and no active mod; "
            "the build refuses patch drift and active mods explicitly.",
        ],
    }
    payloads = {}
    for path, entries in files.items():
        payloads[path] = json.dumps(entries, indent=2) + "\n"
    return darts_section, payloads


def write_outputs(out_root, darts_section, payloads):
    # Byte-exact writes: payloads are encoded once and the same bytes feed
    # the digest records. The darts section is merged into the existing
    # package manifest (prior keys preserved); the manifest cannot digest
    # itself, so only the normalized darts file is digested.
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
    darts_section["outputs"] = outputs
    manifest_path = out / MANIFEST_FILE
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise InputError("package manifest not object")
    manifest["darts"] = darts_section
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
    darts_section, payloads = build_package(repo_root, out_root)
    manifest = write_outputs(out_root, darts_section, payloads)
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
        "counts": manifest["darts"]["counts"],
        "outputs": [entry["file"] for entry in manifest["darts"]["outputs"]],
        "problems": [],
    }
    print(json.dumps(report, indent=2, sort_keys=True) + "\n", end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
