"""Offline offers normalization builder and validator.

Loads the stored legacy offer packs (`offer_packs` from `config/main.json`,
44 entries) directly with no patch layering (no active patch targets the
key; verified per build), preserves every item shape verbatim with a
recorded shape class per the documented offers coercion ruleset (citing
the field-type survey), validates id uniqueness, flat/pair-first/group
references against the committed normalized items legacy-ID set (the
quest-precedent cross-domain edge) outside an exact-match anomaly
allowlist, pair/group structural conformity, and schema-required fields,
and diffs a legacy-shaped re-emission against the stored content exactly
(round-trip fidelity gate). Entry order is preserved; pack semantics are
never interpreted and the two pinned anomalies are preserved verbatim
with manifest notes, never repaired.

On success the normalized offers package (`normalized/offer_packs.json`,
plus the `offers` section merged into `manifest.json`) is written and
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

COERCION_RULESET_VERSION = "offers-coercion-ruleset-v1"
POLICY = "offers-normalization-v1"

MAIN_CONFIG_FILE = Path("config") / "main.json"
PATCH_LIST_FILE = Path("config") / "patch" / "patches.txt"
PATCH_DIR = Path("config") / "patch"
MODS_LIST_FILE = Path("mods") / "mods.txt"
SCHEMA_DIR = Path("packages") / "game-content" / "schemas"
OFFERS_SCHEMA_FILE = SCHEMA_DIR / "offer_pack.schema.json"
NORMALIZED_DIR = Path("packages") / "game-content" / "normalized"
BUILDINGS_FILE = NORMALIZED_DIR / "buildings.json"
UNITS_FILE = NORMALIZED_DIR / "units.json"
SPECIALS_FILE = NORMALIZED_DIR / "specials.json"
OFFERS_FILE = NORMALIZED_DIR / "offer_packs.json"
MANIFEST_FILE = Path("packages") / "game-content" / "manifest.json"

MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_KEYS = 64
MAX_PATCH_FILES = 32
MAX_PATCH_OPS = 4096
MAX_OFFER_ENTRIES = 4096

# Stored offer scalar field sets (field-type survey: mixed with native
# integer amounts, name/type strings, and an items array-or-null holding
# id cross-references). Anything else is content drift.
OFFER_FIELDS = ("id", "cost_cash", "gold", "wood", "steel", "oil", "xp",
                "items", "enabled", "position", "mana", "type", "name")
OFFER_AMOUNTS = ("cost_cash", "gold", "wood", "steel", "oil", "xp", "mana",
                 "enabled", "position")

OFFERS_KEY = "offer_packs"

# Rule F3: exact-match anomaly allowlist (offer id, leaf description).
# (4, "35") is the unresolving pair second in Mistery Box 1; (35, float
# 1072.1224) sits where sibling offers carry 1072 and 1224. Both are
# preserved verbatim with notes; any other unresolving leaf fails.
ANOMALY_OFFER_ID = 4
ANOMALY_PAIR_SECOND = 35
ANOMALY_FLOAT_OFFER_ID = 35
ANOMALY_FLOAT_VALUE = 1072.1224


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


def check_no_offers_patch_targets(root, patch_names):
    """Refuse patch drift: no patch may target offer_packs."""
    for name in patch_names:
        operations = load_patch_operations(root, name)
        for position, operation in enumerate(operations):
            if not isinstance(operation, dict):
                raise InputError("unsupported patch shape: " + name)
            target = operation.get("path")
            if not isinstance(target, str) or not target.startswith("/"):
                raise InputError("unsupported patch target path in " + name)
            key = target[1:].split("/", 1)[0] if len(target) > 1 else ""
            if key == OFFERS_KEY:
                raise InputError(
                    "patch targets offers content in " + name
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


def is_native_int(value):
    """Rule F1: native integers, never booleans."""
    return type(value) is int


def classify_items(items, label):
    """Rule F2: record the shape class of a stored items value."""
    if items is None:
        return "null"
    if not isinstance(items, list) or not items:
        raise ValidationFailure(["items not non-empty array: " + label])
    if all(is_native_int(element) for element in items):
        return "flat"
    if all(isinstance(element, list) and element for element in items):
        if all(len(element) == 2 for element in items):
            return "pairs"
        return "groups"
    raise ValidationFailure(["items not null, flat ints, or nested arrays: "
                             + label])


def coerce_offer(raw, label):
    """Coerce one stored offer_packs entry per rules F1/F2 (verbatim)."""
    if not isinstance(raw, dict):
        raise ValidationFailure(["entry not object: " + label])
    problems = []
    for field in OFFER_FIELDS:
        if field not in raw:
            problems.append("missing field: " + label + "." + field)
    for field in raw:
        if field not in OFFER_FIELDS:
            problems.append("unexpected field: " + label + "." + field)
    if problems:
        raise ValidationFailure(problems)
    if not is_native_int(raw["id"]):
        raise ValidationFailure(["offer id not native integer: " + label])
    body = {"id": raw["id"]}
    for field in OFFER_AMOUNTS:
        if not is_native_int(raw[field]):
            raise ValidationFailure(["field not native integer: " + label + "." + field])
        if raw[field] < 0:
            raise ValidationFailure(["field negative: " + label + "." + field])
        body[field] = raw[field]
    for field in ("name", "type"):
        if not isinstance(raw[field], str):
            raise ValidationFailure(["field not string: " + label + "." + field])
        body[field] = raw[field]
    try:
        shape = classify_items(raw["items"], label)
    except ValidationFailure as failure:
        raise ValidationFailure(failure.problems)
    body["items_shape"] = shape
    body["items"] = copy.deepcopy(raw["items"])
    return body


def resolve_offer_refs(body, items_id_set, label):
    """Rule F3: resolve refs outside the exact-match anomaly allowlist."""
    refs = []
    problems = []
    items = body["items"]
    if body["items_shape"] == "null":
        return refs, problems
    if body["items_shape"] == "flat":
        for value in items:
            if str(value) not in items_id_set:
                problems.append("unresolvable offer item reference: "
                                + label + " -> " + repr(value))
            else:
                refs.append(str(value))
        return refs, problems
    for group in items:
        if body["items_shape"] == "pairs":
            first, second = group
            if not is_native_int(first):
                problems.append("pair first not native integer: " + label)
                continue
            if str(first) not in items_id_set:
                problems.append("unresolvable offer pair reference: "
                                + label + " -> " + repr(first))
            else:
                refs.append(str(first))
            if isinstance(second, bool) or not isinstance(second, (int, float)):
                problems.append("pair second not number: " + label)
            elif body["id"] == ANOMALY_OFFER_ID and second == ANOMALY_PAIR_SECOND:
                continue
            continue
        for value in group:
            if isinstance(value, bool):
                problems.append("group leaf is boolean: " + label)
            elif is_native_int(value):
                if str(value) not in items_id_set:
                    problems.append("unresolvable offer group reference: "
                                    + label + " -> " + repr(value))
                else:
                    refs.append(str(value))
            elif isinstance(value, float):
                if body["id"] == ANOMALY_FLOAT_OFFER_ID and value == ANOMALY_FLOAT_VALUE:
                    continue
                problems.append("unexpected non-integer group leaf: "
                                + label + " -> " + repr(value))
            else:
                problems.append("unexpected group leaf type: "
                                + label + " -> " + repr(value))
    return refs, problems


def build_offer_definition(body, refs, fingerprint):
    return {
        "legacy_id": str(body["id"]),
        "kind": "offer_pack",
        "source_file": MAIN_CONFIG_FILE.as_posix(),
        "source_layer": "stored",
        "content_version": fingerprint,
        "id": body["id"],
        "name": body["name"],
        "type": body["type"],
        "cost_cash": body["cost_cash"],
        "gold": body["gold"],
        "wood": body["wood"],
        "steel": body["steel"],
        "oil": body["oil"],
        "mana": body["mana"],
        "xp": body["xp"],
        "enabled": body["enabled"],
        "position": body["position"],
        "items_shape": body["items_shape"],
        "items": copy.deepcopy(body["items"]),
        "item_refs": list(refs),
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
        if "enum" in spec:
            if isinstance(value, str) and value not in spec["enum"]:
                problems.append("enum mismatch at " + label + "." + field)
            elif isinstance(value, list) and value not in spec["enum"]:
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


def check_round_trip(offers, stored):
    """Diff legacy re-emission against stored content exactly."""
    problems = []
    if len(offers) != len(stored):
        problems.append("round-trip offers count mismatch: %d definitions vs %d stored"
                        % (len(offers), len(stored)))
        return problems
    for definition, original in zip(offers, stored):
        entry_label = "round-trip offer " + definition["legacy_id"]
        if not isinstance(original, dict):
            problems.append(entry_label + ": stored entry not object")
            continue
        if str(original.get("id")) != definition["legacy_id"]:
            problems.append(entry_label + ": order/identity mismatch")
            continue
        try:
            body = coerce_offer(original, "round-trip")
        except ValidationFailure as failure:
            problems.extend([entry_label + ": " + item for item in failure.problems])
            continue
        for field in ("id", "name", "type", "cost_cash", "gold", "wood",
                      "steel", "oil", "mana", "xp", "enabled", "position"):
            if body[field] != definition[field]:
                problems.append(entry_label + ": drift at " + field)
        if body["items_shape"] != definition["items_shape"]:
            problems.append(entry_label + ": drift at items_shape")
        if body["items"] != definition["items"]:
            problems.append(entry_label + ": drift at items")
        if set(original.keys()) != set(OFFER_FIELDS):
            problems.append(entry_label + ": field-set drift "
                            + repr(sorted(set(original.keys()) ^ set(OFFER_FIELDS))))
    return problems


def load_all(root):
    """Load the stored offer packs with patch-drift and mod guards."""
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
    if OFFERS_KEY not in document or not isinstance(document[OFFERS_KEY], list):
        raise InputError("unsupported content shape: offer_packs not array")
    if not document[OFFERS_KEY] or len(document[OFFERS_KEY]) > MAX_OFFER_ENTRIES:
        raise InputError("offers entry limit exceeded")
    patch_names = parse_patch_list(
        read_text_file(root / PATCH_LIST_FILE, "patch list"))
    mods_text = read_text_file(root / MODS_LIST_FILE, "mods list")
    active_mods, inactive_mods = parse_mods_list(mods_text)
    if active_mods:
        raise InputError("active mods unsupported, re-census required: "
                         + ", ".join(active_mods))
    check_no_offers_patch_targets(root, patch_names)
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
        "offer_packs": document[OFFERS_KEY],
        "patch_names": patch_names,
        "active_mods": active_mods,
        "inactive_mods": inactive_mods,
        "items_id_set": items_id_set,
        "items_counts": items_counts,
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
    stored = layers["offer_packs"]
    problems = []
    bodies = []
    for entry in stored:
        label = ("offer id " + repr(entry.get("id"))
                 if isinstance(entry, dict) else "offer entry")
        try:
            bodies.append(coerce_offer(entry, label))
        except ValidationFailure as failure:
            problems.extend(failure.problems)
    if problems:
        raise ValidationFailure(problems)
    offer_ids = [body["id"] for body in bodies]
    if len(set(offer_ids)) != len(offer_ids):
        raise ValidationFailure(["duplicate offer legacy_id in stored offer_packs"])
    offers = []
    shape_counts = {}
    for body in bodies:
        label = "offer id " + repr(body["id"])
        refs, ref_problems = resolve_offer_refs(body, layers["items_id_set"], label)
        problems.extend(ref_problems)
        offers.append(build_offer_definition(body, refs, fingerprint))
        shape_counts[body["items_shape"]] = shape_counts.get(body["items_shape"], 0) + 1
    if problems:
        raise ValidationFailure(problems)
    # The allowlist pins exactly the two documented anomalies; assert both
    # are still present exactly as documented so silent drift cannot hide.
    offers_by_id = {item["id"]: item for item in offers}
    anomaly_four = offers_by_id.get(ANOMALY_OFFER_ID)
    if anomaly_four is None or ANOMALY_PAIR_SECOND not in [
            group[1] for group in anomaly_four["items"]
            if isinstance(group, list) and len(group) == 2]:
        raise ValidationFailure(["pinned anomaly (4, 35) not present as documented"])
    anomaly_float = offers_by_id.get(ANOMALY_FLOAT_OFFER_ID)
    if anomaly_float is None or not any(
            value == ANOMALY_FLOAT_VALUE
            for group in anomaly_float["items"] if isinstance(group, list)
            for value in group):
        raise ValidationFailure(["pinned anomaly (35, 1072.1224) not present as documented"])
    offers_schema = load_schema(root, OFFERS_SCHEMA_FILE.name, "offer_pack")
    for item in offers:
        problems.extend(validate_against_schema(
            item, offers_schema, "offer_pack " + item["legacy_id"]))
    if problems:
        raise ValidationFailure(problems)
    round_problems = check_round_trip(offers, stored)
    if round_problems:
        raise ValidationFailure(round_problems)
    files = {OFFERS_FILE: offers}
    offers_section = {
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
            "offers_patch_targets": "none",
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
            "stored_offers": len(stored),
            "offers": len(offers),
            "shape_counts": shape_counts,
        },
        "anomalies": [
            {"offer_id": ANOMALY_OFFER_ID, "leaf": ANOMALY_PAIR_SECOND,
             "note": "Unresolving pair second in Mistery Box 1; recorded "
                     "opaque, never a reference."},
            {"offer_id": ANOMALY_FLOAT_OFFER_ID, "leaf": ANOMALY_FLOAT_VALUE,
             "note": "Non-integer group leaf where sibling offers carry "
                     "1072 and 1224; preserved verbatim, never repaired."},
        ],
        "validation": {
            "duplicate_ids": 0,
            "amount_violations": 0,
            "missing_fields": 0,
            "round_trip_diffs": 0,
            "unresolvable_references": 0,
        },
        "outputs": [],
        "notes": [
            "Stored offer packs map one-to-one to definitions; scalars "
            "and item shapes are preserved verbatim with per-entry shape "
            "classes null/flat/pairs/groups (rules F1/F2).",
            "Flat leaves, pair firsts, and group integer leaves resolve "
            "against the normalized items legacy-ID set; pair seconds "
            "are opaque numbers (rule F3).",
            "The two pinned anomalies are preserved verbatim under an "
            "exact-match allowlist; any other unresolving leaf fails "
            "validation.",
            "Pack semantics (repetition, pairs, groups) are carried as "
            "observed structures, never decoded as quantities, prices, "
            "weights, or choice rules.",
            "No active patch targets offer_packs; the build refuses "
            "patch drift and active mods explicitly.",
        ],
    }
    payloads = {}
    for path, entries in files.items():
        payloads[path] = json.dumps(entries, indent=2) + "\n"
    return offers_section, payloads


def write_outputs(out_root, offers_section, payloads):
    # Byte-exact writes: payloads are encoded once and the same bytes feed
    # the digest records. The offers section is merged into the existing
    # package manifest (prior keys preserved); the manifest cannot digest
    # itself, so only the normalized offers file is digested.
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
    offers_section["outputs"] = outputs
    manifest_path = out / MANIFEST_FILE
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise InputError("package manifest not object")
    manifest["offers"] = offers_section
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
    offers_section, payloads = build_package(repo_root, out_root)
    manifest = write_outputs(out_root, offers_section, payloads)
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
        "counts": manifest["offers"]["counts"],
        "outputs": [entry["file"] for entry in manifest["offers"]["outputs"]],
        "problems": [],
    }
    print(json.dumps(report, indent=2, sort_keys=True) + "\n", end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
