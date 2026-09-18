"""Offline items-normalization builder and validator.

Loads the stored legacy game-content source (`config/main.json`), mirrors
the legacy loader layering (`get_game_config.py`, never imported) with a
stdlib-only ordered patch application limited to the observed operations,
applies keep-later duplicate cleaning, classifies loaded `items` entries by
their stored `type` field, coerces string-encoded values per the documented
coercion ruleset (citing the field-type survey), validates duplicate IDs,
relation resolution, cost keys/amounts, and schema-required fields, and
diffs a legacy-shaped re-emission against the loaded content modulo the
documented coercions (round-trip fidelity gate).

On success the normalized package (`normalized/buildings.json`,
`normalized/units.json`, `normalized/specials.json`, `manifest.json`) is
written and exit 0 with a JSON report on stdout is returned. Any validation
failure exits 1 without writing output. Invalid input or unsupported shapes
exit 2. Standard library only: no legacy application import, no runtime
save reads, no network, server, browser, or Flash activity.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path
import sys

# Deterministic numeric grammar shared with the field-type survey
# (docs/game-content/field-types.md): optional sign, digits with an optional
# fraction (or a leading-dot fraction), and an optional decimal exponent.
NUMERIC_GRAMMAR = r"[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
NUMERIC_PATTERN = re.compile(NUMERIC_GRAMMAR)

COERCION_RULESET_VERSION = "coercion-ruleset-v1"
POLICY = "items-normalization-v1"

MAIN_CONFIG_FILE = Path("config") / "main.json"
PATCH_LIST_FILE = Path("config") / "patch" / "patches.txt"
PATCH_DIR = Path("config") / "patch"
MODS_LIST_FILE = Path("mods") / "mods.txt"
SCHEMA_DIR = Path("packages") / "game-content" / "schemas"
BUILDING_SCHEMA_FILE = SCHEMA_DIR / "building.schema.json"
UNIT_SCHEMA_FILE = SCHEMA_DIR / "unit.schema.json"
NORMALIZED_DIR = Path("packages") / "game-content" / "normalized"
BUILDINGS_FILE = NORMALIZED_DIR / "buildings.json"
UNITS_FILE = NORMALIZED_DIR / "units.json"
SPECIALS_FILE = NORMALIZED_DIR / "specials.json"
MANIFEST_FILE = Path("packages") / "game-content" / "manifest.json"

MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_KEYS = 64
MAX_PATCH_FILES = 32
MAX_PATCH_OPS = 4096

# Observed patch-operation subset (content census, five ordered patches):
# adds appending to /items/-, adds of patch fields under /items/{index}/,
# one globals add, and one whole-array darts_items replace. Anything else is
# patch drift and fails explicitly instead of mis-applying content.
SUPPORTED_OPS = ("add", "replace")

COST_KEYS = ("o", "s", "g", "w", "c")

# Relation sentinels preserved from stored content: -1 (none) everywhere and
# 0 (none) in 138 upgrades_to and 8 trains_ids entries. Any other value must
# resolve to a known legacy_id.
RELATION_NONE = (-1, 0)

# Body fields in fixed emission order (all 53 stored fields minus id, which
# becomes the envelope legacy_id, minus cost_type, which rule R4 drops).
BODY_FIELDS = [
    "type", "in_store", "name", "cost", "costs", "xp", "display_order",
    "activation", "inventory_ids", "expiration", "collect", "max_collects",
    "collect_type", "category_id", "subcategory_id", "subcat_functional",
    "min_level", "width", "height", "giftable", "max_frame", "img_name",
    "elevation", "unit_capacity", "attack", "defense", "life", "velocity",
    "attack_range", "attack_interval", "new_item", "population",
    "gift_level", "cost_unit_cash", "race", "clicks_to_build", "trains_ids",
    "upgrades_to", "best_against", "best_against_mult", "properties",
    "syringes", "volume", "max_elem_vol", "building_limit_same_id",
    "building_limit_same_scf", "group_type", "training_time",
    "premium_upgrade_costs", "build_time", "collect_xp",
]

INTEGER_FIELDS = frozenset([
    "in_store", "cost", "xp", "display_order", "activation", "expiration",
    "collect", "max_collects", "category_id", "subcategory_id",
    "subcat_functional", "min_level", "width", "height", "giftable",
    "max_frame", "elevation", "unit_capacity", "attack", "defense", "life",
    "velocity", "attack_range", "attack_interval", "new_item", "population",
    "gift_level", "cost_unit_cash", "clicks_to_build", "trains_ids",
    "upgrades_to", "best_against_mult", "syringes", "volume",
    "max_elem_vol", "building_limit_same_id", "building_limit_same_scf",
    "training_time", "build_time", "collect_xp",
])

STRING_FIELDS = frozenset([
    "type", "name", "collect_type", "img_name", "race", "group_type",
])

# Embedded-JSON string fields (rule R2), per the survey profiles.
STRUCT_FIELDS = frozenset([
    "costs", "properties", "inventory_ids", "premium_upgrade_costs",
])

# Patch-added numeric fields (atom_fusion_items_data); optional per entry.
PATCH_FIELDS = ("breeding_order", "sm_training_time")

ENVELOPE_FIELDS = (
    "legacy_id", "kind", "source_file", "source_layer", "content_version",
)

SPECIAL_ID = "925"
SPECIAL_NAME = "Expandable Land"
SPECIAL_NOTE = (
    "Stored type l (land) entry: Expandable Land is terrain inventory, not "
    "a building or unit. It is normalized as a documented special with the "
    "same coercion rules; its empty properties string marks absence of a "
    "property map (rule R3) and its empty group_type is preserved (rule R3)."
)


class InputError(Exception):
    """Invalid input or unsupported shape: exit 2."""


class ValidationFailure(Exception):
    """Content validation failure: exit 1 without writing output."""

    def __init__(self, problems):
        super().__init__("; ".join(problems))
        self.problems = list(problems)


def is_string_encoded_number(value):
    """Return True only for strings fully matching the numeric grammar."""
    return isinstance(value, str) and NUMERIC_PATTERN.fullmatch(value) is not None


def is_embedded_json_string(value):
    """Return True only for non-empty strings the JSON decoder accepts."""
    if not isinstance(value, str) or not value:
        return False
    try:
        json.loads(value)
    except ValueError:
        return False
    return True


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


def load_main_config(root):
    text = read_text_file(root / MAIN_CONFIG_FILE, "content")
    try:
        document = json.loads(text)
    except ValueError:
        raise InputError("content file not valid json")
    if not isinstance(document, dict):
        raise InputError("unsupported content shape: top level not object")
    if not document:
        raise InputError("unsupported content shape: top level empty")
    if len(document) > MAX_TOTAL_KEYS:
        raise InputError("content key limit exceeded")
    if "items" not in document or not isinstance(document["items"], list):
        raise InputError("unsupported content shape: items not array")
    return document

def load_patch_file(root, name):
    text = read_text_file(root / PATCH_DIR / (name + ".json"), "patch " + name)
    try:
        operations = json.loads(text)
    except ValueError:
        raise InputError("patch file not valid json: " + name)
    if not isinstance(operations, list) or not operations:
        raise InputError("unsupported patch shape: " + name)
    if len(operations) > MAX_PATCH_OPS:
        raise InputError("patch operation limit exceeded: " + name)
    op_counts = {}
    for operation in operations:
        if not isinstance(operation, dict):
            raise InputError("unsupported patch shape: " + name)
        op = operation.get("op")
        target = operation.get("path")
        if op not in SUPPORTED_OPS:
            raise InputError("unsupported patch operation in " + name + ": " + repr(op))
        if not isinstance(target, str) or not target.startswith("/"):
            raise InputError("unsupported patch target path in " + name)
        op_counts[op] = op_counts.get(op, 0) + 1
    return operations, op_counts


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


def unescape_pointer_token(token):
    return token.replace("~1", "/").replace("~0", "~")


def apply_patch_op(document, operation, name, position):
    """Apply one observed patch op; anything else is drift (exit 2)."""
    op = operation.get("op")
    target = operation.get("path")
    if op == "add" and target == "/items/-":
        value = operation.get("value")
        if not isinstance(value, dict):
            raise InputError("unsupported appended item shape in " + name)
        document["items"].append(value)
        return ("append", None)
    if op == "add" and target.startswith("/items/"):
        parts = target.split("/")
        if len(parts) == 4 and parts[2].isdigit():
            index = int(parts[2])
            field = unescape_pointer_token(parts[3])
            if not field or "/" in parts[3]:
                raise InputError("unsupported patch target path in " + name)
            items = document["items"]
            if not 0 <= index < len(items):
                raise InputError("patch index out of range in " + name + ": " + target)
            if not isinstance(items[index], dict):
                raise InputError("unsupported items entry shape in " + name)
            items[index][field] = operation.get("value")
            return ("set-field", (index, field))
    if op == "add" and target.startswith("/globals/"):
        parts = target.split("/")
        if len(parts) == 3 and parts[2]:
            key = unescape_pointer_token(parts[2])
            if not isinstance(document.get("globals"), dict):
                raise InputError("unsupported globals shape in " + name)
            document["globals"][key] = operation.get("value")
            return ("set-global", key)
    if op == "replace" and target == "/darts_items":
        value = operation.get("value")
        if not isinstance(value, list):
            raise InputError("unsupported darts_items shape in " + name)
        document["darts_items"] = value
        return ("replace-array", "darts_items")
    raise InputError(
        "unsupported patch operation in " + name + " at position " + str(position)
        + ": " + repr(op) + " " + repr(target))


def dedup_keep_later(pairs):
    """Mirror remove_duplicate_items over (entry, origin) pairs.

    The legacy cleaner deletes the earlier of two entries sharing an id
    and keeps the later one; the net effect is keep-last per id in
    last-occurrence order. Origins travel with their entries so layering
    attribution survives cleaning.
    """
    kept = []
    indexes = {}
    removed = 0
    for entry, origin in pairs:
        if not isinstance(entry, dict) or "id" not in entry:
            raise InputError("unsupported items entry shape for dedup")
        item_id = entry["id"]
        if item_id in indexes:
            kept[indexes[item_id]] = None
            removed += 1
        indexes[item_id] = len(kept)
        kept.append((entry, origin))
    return [pair for pair in kept if pair is not None], removed


def coerce_number_text(text, label):
    """Rule R1: numeric strings to numbers, integral floats to int."""
    if not is_string_encoded_number(text):
        raise ValidationFailure(["field not numeric string: " + label + " = " + repr(text)])
    try:
        number = float(text)
    except ValueError:
        raise ValidationFailure(["field not numeric string: " + label + " = " + repr(text)])
    if number.is_integer():
        return int(number)
    return number


def coerce_item(raw, label):
    """Coerce one loaded items entry per rules R1/R2/R3/R5; R4 drops cost_type."""
    if not isinstance(raw, dict):
        raise ValidationFailure(["entry not object: " + label])
    problems = []
    for field in BODY_FIELDS + ["id"]:
        if field not in raw:
            problems.append("missing field: " + label + "." + field)
    if "cost_type" not in raw:
        problems.append("missing field: " + label + ".cost_type")
    if problems:
        raise ValidationFailure(problems)
    if raw["cost_type"] is not None:
        raise ValidationFailure(["cost_type not null, rule R4: " + label])
    body = {}
    for field in BODY_FIELDS:
        value = raw[field]
        if field in INTEGER_FIELDS:
            if not isinstance(value, str):
                raise ValidationFailure([
                    "field not string-encoded: " + label + "." + field])
            body[field] = coerce_number_text(value, label + "." + field)
        elif field in STRING_FIELDS:
            if not isinstance(value, str):
                raise ValidationFailure([
                    "field not string: " + label + "." + field])
            body[field] = value
        elif field == "costs":
            if not isinstance(value, str) or not is_embedded_json_string(value):
                raise ValidationFailure(["costs not embedded json: " + label])
            parsed = json.loads(value)
            if not isinstance(parsed, dict):
                raise ValidationFailure(["costs not object: " + label])
            for key, amount in parsed.items():
                if key not in COST_KEYS:
                    raise ValidationFailure([
                        "cost key outside o/s/g/w/c: " + label + " key " + repr(key)])
                if type(amount) is not int or amount < 0:
                    raise ValidationFailure([
                        "cost amount not non-negative int: " + label
                        + " key " + repr(key)])
            body[field] = parsed
        elif field == "properties":
            if value == "":
                body[field] = None
            elif isinstance(value, str) and is_embedded_json_string(value):
                parsed = json.loads(value)
                if not isinstance(parsed, dict):
                    raise ValidationFailure(["properties not object: " + label])
                body[field] = parsed
            else:
                raise ValidationFailure(["properties not object string: " + label])
        elif field == "inventory_ids":
            if not isinstance(value, str) or not is_embedded_json_string(value):
                raise ValidationFailure(["inventory_ids not embedded json: " + label])
            parsed = json.loads(value)
            if parsed is not None and not isinstance(parsed, dict):
                raise ValidationFailure(["inventory_ids not object/null: " + label])
            body[field] = parsed
        elif field == "premium_upgrade_costs":
            if value == "":
                body[field] = None
            elif isinstance(value, str) and is_embedded_json_string(value):
                parsed = json.loads(value)
                if not isinstance(parsed, dict):
                    raise ValidationFailure([
                        "premium_upgrade_costs not object: " + label])
                body[field] = parsed
            else:
                raise ValidationFailure([
                    "premium_upgrade_costs not object string: " + label])
        elif field == "best_against":
            if not isinstance(value, str):
                raise ValidationFailure(["field not string: " + label + "." + field])
            if value != "" and is_string_encoded_number(value):
                body[field] = coerce_number_text(value, label + "." + field)
            else:
                body[field] = value
        else:  # pragma: no cover - BODY_FIELDS partition guard
            raise ValidationFailure(["unclassified field: " + label + "." + field])
    for field in PATCH_FIELDS:
        if field in raw:
            value = raw[field]
            if not isinstance(value, str):
                raise ValidationFailure([
                    "field not string-encoded: " + label + "." + field])
            body[field] = coerce_number_text(value, label + "." + field)
    return body

def classify_and_build(body, legacy_id, origin_file, origin_layer, fingerprint):
    stored_type = body["type"]
    if stored_type == "b":
        kind = "building"
    elif stored_type == "u":
        kind = "unit"
    elif stored_type == "l":
        kind = "special"
    else:
        raise ValidationFailure([
            "unknown type for id " + legacy_id + ": " + repr(stored_type)])
    definition = {
        "legacy_id": legacy_id,
        "kind": kind,
        "source_file": origin_file,
        "source_layer": origin_layer,
        "content_version": fingerprint,
    }
    definition.update(body)
    if kind == "special":
        definition["special_note"] = SPECIAL_NOTE
    return definition


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
    """Enforce schema required/type/const/enum/minimum/propertyNames gates."""
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
        names = spec.get("propertyNames")
        if isinstance(value, dict) and isinstance(names, dict):
            allowed_names = names.get("enum", [])
            for key in value:
                if key not in allowed_names:
                    problems.append("property name outside set at " + label
                                    + "." + field + ": " + repr(key))
        additional = spec.get("additionalProperties")
        if isinstance(value, dict) and isinstance(additional, dict):
            for key, amount in value.items():
                if "type" in additional:
                    sub = []
                    check_schema_type(amount, [additional["type"]],
                                      label + "." + field + "." + str(key), sub)
                    problems.extend(sub)
                if "minimum" in additional and isinstance(amount, (int, float)):
                    if not isinstance(amount, bool) and amount < additional["minimum"]:
                        problems.append("value below minimum at " + label + "."
                                        + field + "." + str(key))
    if schema.get("additionalProperties") is False:
        for field in definition:
            if field not in schema["properties"]:
                problems.append("additional property: " + label + "." + field)
    return problems


def validate_relations(definition, known_ids):
    """Upgrades/trains references resolve unless they are -1/0 sentinels."""
    problems = []
    legacy_id = definition["legacy_id"]
    for field in ("upgrades_to", "trains_ids"):
        value = definition[field]
        if value in RELATION_NONE:
            continue
        if str(value) not in known_ids:
            problems.append("unresolvable " + field + " for id " + legacy_id
                            + ": " + repr(value))
    return problems


def check_round_trip(definitions, loaded_items):
    """Diff legacy re-emission against loaded content modulo coercions."""
    problems = []
    if len(definitions) != len(loaded_items):
        return ["round-trip count mismatch: %d definitions vs %d loaded"
                % (len(definitions), len(loaded_items))]
    for definition, original in zip(definitions, loaded_items):
        label = "round-trip id " + definition["legacy_id"]
        if original.get("id") != definition["legacy_id"]:
            problems.append(label + ": order/identity mismatch")
            continue
        try:
            body = coerce_item(original, "round-trip")
        except ValidationFailure as failure:
            problems.extend([label + ": " + item for item in failure.problems])
            continue
        for field in BODY_FIELDS:
            expected = body[field]
            actual = definition[field]
            if isinstance(expected, float) or isinstance(actual, float):
                if not (isinstance(expected, (int, float))
                        and isinstance(actual, (int, float))
                        and float(expected) == float(actual)):
                    problems.append(label + ": numeric drift at " + field)
            elif expected != actual:
                problems.append(label + ": drift at " + field)
        for field in PATCH_FIELDS:
            if (field in body) != (field in definition):
                problems.append(label + ": patch-field presence drift at " + field)
            elif field in body and body[field] != definition[field]:
                problems.append(label + ": patch-field drift at " + field)
        if original.get("cost_type") is not None:
            problems.append(label + ": cost_type not null")
        expected_keys = {"id", "cost_type"} | set(BODY_FIELDS) | {
            field for field in PATCH_FIELDS if field in original}
        if set(original.keys()) != expected_keys:
            problems.append(label + ": field-set drift "
                            + repr(sorted(set(original.keys()) ^ expected_keys)))
    return problems

def load_all(root):
    """Load stored content, apply ordered patches, dedup; return layers."""
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
    if "items" not in document or not isinstance(document["items"], list):
        raise InputError("unsupported content shape: items not array")
    stored_count = len(document["items"])
    patch_names = parse_patch_list(
        read_text_file(root / PATCH_LIST_FILE, "patch list"))
    mods_text = read_text_file(root / MODS_LIST_FILE, "mods list")
    active_mods, inactive_mods = parse_mods_list(mods_text)
    if active_mods:
        raise InputError("active mods unsupported, re-census required: "
                         + ", ".join(active_mods))
    patch_infos = []
    origins = ["stored"] * stored_count
    for position, name in enumerate(patch_names, start=1):
        operations, op_counts = load_patch_file(root, name)
        touched = 0
        for index, operation in enumerate(operations):
            effect = apply_patch_op(document, operation, name, index)
            if effect[0] == "append":
                origins.append("patch:" + name + ":" + str(position))
                touched += 1
        patch_infos.append({
            "name": name,
            "file": (PATCH_DIR / (name + ".json")).as_posix(),
            "position": position,
            "op_count": len(operations),
            "op_counts": op_counts,
            "appended_items": touched,
        })
    # Keep-later duplicate cleaning is mirrored, but normalization refuses to
    # silently drop definitions: any removal fails validation downstream.
    pairs, removed = dedup_keep_later(list(zip(document["items"], origins)))
    loaded = [entry for entry, _origin in pairs]
    origins = [origin for _entry, origin in pairs]
    return {
        "items": loaded,
        "origins": origins,
        "stored_count": stored_count,
        "patch_names": patch_names,
        "patch_infos": patch_infos,
        "active_mods": active_mods,
        "inactive_mods": inactive_mods,
        "duplicates_removed": removed,
        "main_bytes": main_bytes,
    }


def fingerprint_inputs(root, layers):
    digest = hashlib.sha256()
    digest.update(layers["main_bytes"])
    digest.update(read_bytes_file(root / PATCH_LIST_FILE, "patch list"))
    for name in layers["patch_names"]:
        digest.update(read_bytes_file(root / PATCH_DIR / (name + ".json"),
                                      "patch " + name))
    digest.update(read_bytes_file(root / MODS_LIST_FILE, "mods list"))
    return digest.hexdigest()


def build_package(repo_root, out_root):
    """Build in memory, validate everything, then write output files."""
    root = Path(repo_root)
    out = Path(out_root)
    layers = load_all(root)
    fingerprint = fingerprint_inputs(root, layers)
    items = layers["items"]
    origins = layers["origins"]
    problems = []
    if layers["duplicates_removed"]:
        problems.append("duplicate item ids removed by dedup: "
                        + str(layers["duplicates_removed"])
                        + "; refusing silent loss")
    bodies = []
    for entry, origin in zip(items, origins):
        label = "item id " + repr(entry.get("id") if isinstance(entry, dict) else entry)
        try:
            body = coerce_item(entry, label)
        except ValidationFailure as failure:
            problems.extend(failure.problems)
            continue
        if origin == "stored":
            origin_file = MAIN_CONFIG_FILE.as_posix()
            origin_layer = "stored"
        else:
            _, patch_name, position = origin.split(":")
            origin_file = (PATCH_DIR / (patch_name + ".json")).as_posix()
            origin_layer = "patch:" + patch_name + ":" + position
        try:
            bodies.append(classify_and_build(
                body, entry["id"], origin_file, origin_layer, fingerprint))
        except ValidationFailure as failure:
            problems.extend(failure.problems)
    if problems:
        raise ValidationFailure(problems)
    known_ids = {item["legacy_id"] for item in bodies}
    if len(known_ids) != len(bodies):
        raise ValidationFailure(["duplicate legacy_id in normalized output"])
    building_schema = load_schema(root, BUILDING_SCHEMA_FILE.name, "building")
    unit_schema = load_schema(root, UNIT_SCHEMA_FILE.name, "unit")
    buildings = [item for item in bodies if item["kind"] == "building"]
    units = [item for item in bodies if item["kind"] == "unit"]
    specials = [item for item in bodies if item["kind"] == "special"]
    for item in buildings:
        problems.extend(validate_against_schema(
            item, building_schema, "building " + item["legacy_id"]))
        problems.extend(validate_relations(item, known_ids))
    for item in units:
        problems.extend(validate_against_schema(
            item, unit_schema, "unit " + item["legacy_id"]))
        problems.extend(validate_relations(item, known_ids))
    for item in specials:
        if item["legacy_id"] != SPECIAL_ID:
            problems.append("unexpected special id: " + item["legacy_id"])
        if item.get("special_note") != SPECIAL_NOTE:
            problems.append("special note missing for id " + item["legacy_id"])
        problems.extend(validate_relations(item, known_ids))
    if len(specials) != 1 or (specials and specials[0]["legacy_id"] != SPECIAL_ID):
        problems.append("expected exactly the id 925 special, found "
                        + str(len(specials)))
    else:
        special = specials[0]
        if special.get("name") != SPECIAL_NAME or special.get("type") != "l":
            problems.append("special 925 identity drift")
    if problems:
        raise ValidationFailure(problems)
    round_problems = check_round_trip(bodies, items)
    if round_problems:
        raise ValidationFailure(round_problems)
    with_breeding = sum(1 for item in bodies if "breeding_order" in item)
    upgrades = sum(1 for item in bodies if item["upgrades_to"] not in (-1, 0))
    trains = sum(1 for item in bodies if item["trains_ids"] not in (-1, 0))
    files = {
        BUILDINGS_FILE: buildings,
        UNITS_FILE: units,
        SPECIALS_FILE: specials,
    }
    manifest = {
        "schema_version": 1,
        "policy": POLICY,
        "result": "success",
        "inputs": {
            "main": {
                "file": MAIN_CONFIG_FILE.as_posix(),
                "bytes": len(layers["main_bytes"]),
                "sha256": hashlib.sha256(layers["main_bytes"]).hexdigest(),
            },
            "patch_list": {
                "file": PATCH_LIST_FILE.as_posix(),
                "order": layers["patch_names"],
            },
            "patches": layers["patch_infos"],
            "mods": {
                "status": "inactive",
                "active_mods": layers["active_mods"],
                "inactive_mods": layers["inactive_mods"],
            },
        },
        "layering": {
            "order": layers["patch_names"],
            "duplicates_removed": layers["duplicates_removed"],
        },
        "coercion_ruleset": COERCION_RULESET_VERSION,
        "content_fingerprint": fingerprint,
        "counts": {
            "stored_items": layers["stored_count"],
            "appended_items": sum(info["appended_items"]
                                  for info in layers["patch_infos"]),
            "loaded_items": len(items),
            "buildings": len(buildings),
            "units": len(units),
            "specials": len(specials),
            "with_breeding_fields": with_breeding,
            "upgrades_nontrivial": upgrades,
            "trains_nondefault": trains,
        },
        "validation": {
            "duplicate_ids": 0,
            "unresolvable_references": 0,
            "cost_violations": 0,
            "missing_fields": 0,
            "round_trip_diffs": 0,
        },
        "outputs": [],
        "notes": [
            "cost_type (null in every stored and appended entry) dropped, rule R4.",
            "costs carry one or more resource keys within o/s/g/w/c; "
            "single-key dominance is not assumed.",
            "upgrades_to/trains_ids values -1 and 0 mean none; other "
            "values resolve to known legacy_id entries.",
            "best_against numerics are opaque codes (verified "
            "non-resolving against item ids), not item references.",
            "inventory_ids keys reference the inventory_items domain, not "
            "item ids, and are carried as structures without item-id checks.",
            "breeding_order/sm_training_time exist only where "
            "atom_fusion_items_data added them.",
        ],
    }
    payloads = {}
    for path, entries in files.items():
        payloads[path] = json.dumps(entries, indent=2) + "\n"
    manifest_payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    return manifest, payloads, manifest_payload


def write_outputs(out_root, manifest, payloads, manifest_payload):
    # Byte-exact writes: payloads are encoded once and the same bytes feed
    # the digest records, so outputs never need re-reading (the manifest
    # records only the three normalized files; it cannot digest itself).
    _ = manifest_payload
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
    manifest["outputs"] = outputs
    final_payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    (out / MANIFEST_FILE).write_bytes(final_payload.encode("utf-8"))
    return manifest


def build_argument_parser():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--repo-root",
                        help="repository root to read (default: current directory)")
    parser.add_argument("--out-root",
                        help="package root to write (default: same as repo root)")
    return parser


def run_build(repo_root, out_root):
    manifest, payloads, manifest_payload = build_package(repo_root, out_root)
    manifest = write_outputs(out_root, manifest, payloads, manifest_payload)
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
        "counts": manifest["counts"],
        "outputs": [entry["file"] for entry in manifest["outputs"]],
        "problems": [],
    }
    print(json.dumps(report, indent=2, sort_keys=True) + "\n", end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())



