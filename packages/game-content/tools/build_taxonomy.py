"""Offline inventory-taxonomy normalization builder and validator.

Loads the stored legacy object-keyed classification content
(`inventory_items`, `categories`, and `units_collections_categories` from
`config/main.json`) directly with no patch layering (no active patch
targets any of the three keys; verified per build), coerces
string-encoded numerics per the documented taxonomy coercion ruleset
(citing the field-type survey), validates key uniqueness, non-negative
amounts, collection unit references against the committed normalized
items legacy-ID set, stored item `inventory_ids` keys against the
normalized inventory key set (both quest-precedent cross-domain edges),
and schema-required fields, and diffs a legacy-shaped re-emission
against the stored content modulo the documented coercions (round-trip
fidelity gate). Object keys are the identity and stored document order
is preserved; the single null `costs`, the uniformly-empty
`category_name_el`, and the unresolving patch-era item category codes
are carried with manifest notes, never repaired.

On success the normalized taxonomy package
(`normalized/inventory_items.json`, `normalized/categories.json`,
`normalized/unit_collection_categories.json`, plus the `taxonomy`
section merged into `manifest.json`) is written and exit 0 with a JSON
report on stdout is returned. Any validation failure exits 1 without
writing output. Invalid input or unsupported shapes exit 2. Standard
library only: no legacy application import, no runtime save reads, no
network, server, browser, or Flash activity.
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

COERCION_RULESET_VERSION = "taxonomy-coercion-ruleset-v1"
POLICY = "taxonomy-normalization-v1"

MAIN_CONFIG_FILE = Path("config") / "main.json"
PATCH_LIST_FILE = Path("config") / "patch" / "patches.txt"
PATCH_DIR = Path("config") / "patch"
MODS_LIST_FILE = Path("mods") / "mods.txt"
SCHEMA_DIR = Path("packages") / "game-content" / "schemas"
INVENTORY_SCHEMA_FILE = SCHEMA_DIR / "inventory_item.schema.json"
CATEGORY_SCHEMA_FILE = SCHEMA_DIR / "category.schema.json"
COLLECTION_SCHEMA_FILE = SCHEMA_DIR / "unit_collection_category.schema.json"
NORMALIZED_DIR = Path("packages") / "game-content" / "normalized"
BUILDINGS_FILE = NORMALIZED_DIR / "buildings.json"
UNITS_FILE = NORMALIZED_DIR / "units.json"
SPECIALS_FILE = NORMALIZED_DIR / "specials.json"
INVENTORY_FILE = NORMALIZED_DIR / "inventory_items.json"
CATEGORIES_FILE = NORMALIZED_DIR / "categories.json"
COLLECTIONS_FILE = NORMALIZED_DIR / "unit_collection_categories.json"
MANIFEST_FILE = Path("packages") / "game-content" / "manifest.json"

MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_KEYS = 64
MAX_PATCH_FILES = 32
MAX_PATCH_OPS = 4096
MAX_TAXONOMY_ENTRIES = 4096

# Stored object field sets (field-type survey: inventory_items object with
# 7 string fields; categories object with id/name/sub; collections object
# with 14 mixed fields). Anything else is content drift.
INVENTORY_FIELDS = ("id", "name", "cashPrice", "droppable", "dropRate",
                    "dropsFrom", "description")
CATEGORY_FIELDS = ("id", "name", "sub")
SUB_FIELDS = ("id", "name", "parent")
COLLECTION_FIELDS = ("category_id", "units", "rewards", "cost", "costs",
                     "position", "category_name", "category_name_es",
                     "category_name_br", "category_name_it",
                     "category_name_fr", "category_name_de",
                     "category_name_tr", "category_name_el")
COLLECTION_NAMES = ("category_name", "category_name_es", "category_name_br",
                    "category_name_it", "category_name_fr",
                    "category_name_de", "category_name_tr",
                    "category_name_el")

TAXONOMY_KEYS = ("inventory_items", "categories",
                 "units_collections_categories")


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


def check_no_taxonomy_patch_targets(root, patch_names):
    """Refuse patch drift: no patch may target the three taxonomy keys."""
    for name in patch_names:
        operations = load_patch_operations(root, name)
        for position, operation in enumerate(operations):
            if not isinstance(operation, dict):
                raise InputError("unsupported patch shape: " + name)
            target = operation.get("path")
            if not isinstance(target, str) or not target.startswith("/"):
                raise InputError("unsupported patch target path in " + name)
            key = target[1:].split("/", 1)[0] if len(target) > 1 else ""
            if key in TAXONOMY_KEYS:
                raise InputError(
                    "patch targets taxonomy content in " + name
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


def coerce_number_text(text, label):
    """Rule N1: numeric strings to numbers, integral floats to int."""
    if not is_string_encoded_number(text):
        raise ValidationFailure(["field not numeric string: " + label + " = " + repr(text)])
    try:
        number = float(text)
    except ValueError:
        raise ValidationFailure(["field not numeric string: " + label + " = " + repr(text)])
    if number.is_integer():
        return int(number)
    return number


def coerce_inventory(raw, key, label):
    """Coerce one stored inventory_items entry per rule N1."""
    if not isinstance(raw, dict):
        raise ValidationFailure(["entry not object: " + label])
    problems = []
    for field in INVENTORY_FIELDS:
        if field not in raw:
            problems.append("missing field: " + label + "." + field)
    for field in raw:
        if field not in INVENTORY_FIELDS:
            problems.append("unexpected field: " + label + "." + field)
    if problems:
        raise ValidationFailure(problems)
    body = {}
    for field in ("id", "cashPrice", "droppable", "dropRate", "dropsFrom"):
        if not isinstance(raw[field], str):
            raise ValidationFailure([field + " not string-encoded: " + label])
        value = coerce_number_text(raw[field], label + "." + field)
        if type(value) is not int:
            raise ValidationFailure([field + " not integral: " + label])
        if value < 0:
            raise ValidationFailure([field + " negative: " + label])
        body[field] = value
    for field in ("name", "description"):
        if not isinstance(raw[field], str):
            raise ValidationFailure(["field not string: " + label + "." + field])
        body[field] = raw[field]
    if str(body["id"]) != key:
        raise ValidationFailure(["inventory id/key mismatch: " + label])
    return body


def coerce_category(raw, key, label):
    """Coerce one stored categories entry per rule N3 (verbatim)."""
    if not isinstance(raw, dict):
        raise ValidationFailure(["entry not object: " + label])
    problems = []
    for field in CATEGORY_FIELDS:
        if field not in raw:
            problems.append("missing field: " + label + "." + field)
    for field in raw:
        if field not in CATEGORY_FIELDS:
            problems.append("unexpected field: " + label + "." + field)
    if problems:
        raise ValidationFailure(problems)
    if type(raw["id"]) is not int:
        raise ValidationFailure(["category id not native integer: " + label])
    if str(raw["id"]) != key:
        raise ValidationFailure(["category id/key mismatch: " + label])
    if not isinstance(raw["name"], str):
        raise ValidationFailure(["field not string: " + label + ".name"])
    sub = raw["sub"]
    if not isinstance(sub, list) or not sub:
        raise ValidationFailure(["sub not non-empty array: " + label])
    entries = []
    for position, item in enumerate(sub):
        entry_label = label + ".sub[" + str(position) + "]"
        if not isinstance(item, dict):
            raise ValidationFailure(["sub entry not object: " + entry_label])
        for field in SUB_FIELDS:
            if field not in item:
                raise ValidationFailure(["missing field: " + entry_label + "." + field])
        for field in item:
            if field not in SUB_FIELDS:
                raise ValidationFailure(["unexpected field: " + entry_label + "." + field])
        if type(item["id"]) is not int:
            raise ValidationFailure(["sub id not native integer: " + entry_label])
        if not isinstance(item["name"], str):
            raise ValidationFailure(["sub name not string: " + entry_label])
        if type(item["parent"]) is not int:
            raise ValidationFailure(["sub parent not native integer: " + entry_label])
        if item["parent"] != raw["id"]:
            raise ValidationFailure(["sub parent mismatch: " + entry_label])
        entries.append({"id": item["id"], "name": item["name"],
                        "parent": item["parent"]})
    return {"id": raw["id"], "name": raw["name"], "sub": entries}


def coerce_collection(raw, key, label):
    """Coerce one stored units_collections_categories entry per rule N3."""
    if not isinstance(raw, dict):
        raise ValidationFailure(["entry not object: " + label])
    problems = []
    for field in COLLECTION_FIELDS:
        if field not in raw:
            problems.append("missing field: " + label + "." + field)
    for field in raw:
        if field not in COLLECTION_FIELDS:
            problems.append("unexpected field: " + label + "." + field)
    if problems:
        raise ValidationFailure(problems)
    if type(raw["category_id"]) is not int:
        raise ValidationFailure(["category_id not native integer: " + label])
    if str(raw["category_id"]) != key:
        raise ValidationFailure(["category id/key mismatch: " + label])
    for field in ("rewards", "cost", "position"):
        if type(raw[field]) is not int:
            raise ValidationFailure(["field not native integer: " + label + "." + field])
        if raw[field] < 0:
            raise ValidationFailure(["field negative: " + label + "." + field])
    units = raw["units"]
    if not isinstance(units, list) or not units:
        raise ValidationFailure(["units not non-empty array: " + label])
    for value in units:
        if type(value) is not int:
            raise ValidationFailure(["units element not integer: " + label])
    costs = raw["costs"]
    if costs is not None:
        if not isinstance(costs, list) or not costs:
            raise ValidationFailure(["costs not non-empty array: " + label])
        for value in costs:
            if type(value) is not int:
                raise ValidationFailure(["costs element not integer: " + label])
            if value < 0:
                raise ValidationFailure(["costs element negative: " + label])
    for field in COLLECTION_NAMES:
        if not isinstance(raw[field], str):
            raise ValidationFailure(["field not string: " + label + "." + field])
    return {
        "category_id": raw["category_id"],
        "units": list(units),
        "unit_refs": [str(value) for value in units],
        "rewards": raw["rewards"],
        "cost": raw["cost"],
        "costs": None if costs is None else list(costs),
        "position": raw["position"],
        "names": {field: raw[field] for field in COLLECTION_NAMES},
    }


def build_inventory_definition(body, key, fingerprint):
    return {
        "legacy_id": key,
        "kind": "inventory_item",
        "source_file": MAIN_CONFIG_FILE.as_posix(),
        "source_layer": "stored",
        "content_version": fingerprint,
        "id": body["id"],
        "name": body["name"],
        "cashPrice": body["cashPrice"],
        "droppable": body["droppable"],
        "dropRate": body["dropRate"],
        "dropsFrom": body["dropsFrom"],
        "description": body["description"],
    }


def build_category_definition(body, key, fingerprint):
    return {
        "legacy_id": key,
        "kind": "category",
        "source_file": MAIN_CONFIG_FILE.as_posix(),
        "source_layer": "stored",
        "content_version": fingerprint,
        "id": body["id"],
        "name": body["name"],
        "sub": [dict(entry) for entry in body["sub"]],
    }


def build_collection_definition(body, key, fingerprint):
    definition = {
        "legacy_id": key,
        "kind": "unit_collection_category",
        "source_file": MAIN_CONFIG_FILE.as_posix(),
        "source_layer": "stored",
        "content_version": fingerprint,
        "category_id": body["category_id"],
        "units": list(body["units"]),
        "unit_refs": list(body["unit_refs"]),
        "rewards": body["rewards"],
        "cost": body["cost"],
        "costs": body["costs"],
        "position": body["position"],
    }
    for field in COLLECTION_NAMES:
        definition[field] = body["names"][field]
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


def validate_collection_references(collections, items_id_set):
    """Rule N3: every collection units integer must resolve to an item."""
    problems = []
    for definition in collections:
        for key in definition["unit_refs"]:
            if key not in items_id_set:
                problems.append("unresolvable collection unit reference: "
                                + definition["legacy_id"] + " -> " + key)
        if definition["unit_refs"] != [str(value) for value in definition["units"]]:
            problems.append("unit_refs drift at collection "
                            + definition["legacy_id"])
    return problems


def validate_inventory_references(loaded_items, inventory_keys):
    """Rule N3: every stored/appended inventory_ids object key must resolve."""
    problems = []
    for position, entry in enumerate(loaded_items):
        if not isinstance(entry, dict):
            problems.append("loaded item not object at index " + str(position))
            continue
        raw = entry.get("inventory_ids")
        if raw == "null":
            continue
        if not isinstance(raw, str) or not is_embedded_json_string(raw):
            problems.append("inventory_ids not null-or-embedded-json at item "
                            + repr(entry.get("id")))
            continue
        try:
            parsed = json.loads(raw)
        except ValueError:
            problems.append("inventory_ids unparseable at item "
                            + repr(entry.get("id")))
            continue
        if not isinstance(parsed, dict):
            problems.append("inventory_ids not object at item "
                            + repr(entry.get("id")))
            continue
        for key in parsed.keys():
            if key not in inventory_keys:
                problems.append("unresolvable inventory_ids key: "
                                + repr(entry.get("id")) + " -> " + key)
    return problems


def check_round_trip(inventory, categories, collections, ordered_keys,
                     stored_inventory, stored_categories, stored_collections):
    """Diff legacy re-emission against stored content modulo coercions."""
    problems = []
    triples = (
        ("inventory item", inventory, stored_inventory, "inventory_items"),
        ("category", categories, stored_categories, "categories"),
        ("collection", collections, stored_collections,
         "units_collections_categories"),
    )
    for label, definitions, stored, _key in triples:
        if [item["legacy_id"] for item in definitions] != ordered_keys[label]:
            problems.append("round-trip " + label + " key order mismatch")
    for definition, key in zip(inventory, ordered_keys["inventory item"]):
        entry_label = "round-trip inventory " + definition["legacy_id"]
        original = stored_inventory.get(key)
        if not isinstance(original, dict):
            problems.append(entry_label + ": stored entry not object")
            continue
        try:
            body = coerce_inventory(original, key, "round-trip")
        except ValidationFailure as failure:
            problems.extend([entry_label + ": " + item for item in failure.problems])
            continue
        for field in ("id", "name", "cashPrice", "droppable", "dropRate",
                      "dropsFrom", "description"):
            if body[field] != definition[field]:
                problems.append(entry_label + ": drift at " + field)
        if set(original.keys()) != set(INVENTORY_FIELDS):
            problems.append(entry_label + ": field-set drift "
                            + repr(sorted(set(original.keys()) ^ set(INVENTORY_FIELDS))))
    for definition, key in zip(categories, ordered_keys["category"]):
        entry_label = "round-trip category " + definition["legacy_id"]
        original = stored_categories.get(key)
        if not isinstance(original, dict):
            problems.append(entry_label + ": stored entry not object")
            continue
        try:
            body = coerce_category(original, key, "round-trip")
        except ValidationFailure as failure:
            problems.extend([entry_label + ": " + item for item in failure.problems])
            continue
        if body["id"] != definition["id"] or body["name"] != definition["name"]:
            problems.append(entry_label + ": drift at id/name")
        if body["sub"] != definition["sub"]:
            problems.append(entry_label + ": drift at sub")
        if set(original.keys()) != set(CATEGORY_FIELDS):
            problems.append(entry_label + ": field-set drift "
                            + repr(sorted(set(original.keys()) ^ set(CATEGORY_FIELDS))))
    for definition, key in zip(collections, ordered_keys["collection"]):
        entry_label = "round-trip collection " + definition["legacy_id"]
        original = stored_collections.get(key)
        if not isinstance(original, dict):
            problems.append(entry_label + ": stored entry not object")
            continue
        try:
            body = coerce_collection(original, key, "round-trip")
        except ValidationFailure as failure:
            problems.extend([entry_label + ": " + item for item in failure.problems])
            continue
        for field in ("category_id", "units", "rewards", "cost", "costs",
                      "position"):
            if body[field] != definition[field]:
                problems.append(entry_label + ": drift at " + field)
        if body["unit_refs"] != definition["unit_refs"]:
            problems.append(entry_label + ": drift at unit_refs")
        for field in COLLECTION_NAMES:
            if body["names"][field] != definition[field]:
                problems.append(entry_label + ": drift at " + field)
        if set(original.keys()) != set(COLLECTION_FIELDS):
            problems.append(entry_label + ": field-set drift "
                            + repr(sorted(set(original.keys()) ^ set(COLLECTION_FIELDS))))
    return problems


def load_all(root):
    """Load the stored taxonomy objects with patch-drift and mod guards."""
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
    for key in TAXONOMY_KEYS:
        if key not in document or not isinstance(document[key], dict):
            raise InputError("unsupported content shape: " + key + " not object")
        if not document[key] or len(document[key]) > MAX_TAXONOMY_ENTRIES:
            raise InputError("taxonomy entry limit exceeded: " + key)
    if "items" not in document or not isinstance(document["items"], list):
        raise InputError("unsupported content shape: items not array")
    patch_names = parse_patch_list(
        read_text_file(root / PATCH_LIST_FILE, "patch list"))
    mods_text = read_text_file(root / MODS_LIST_FILE, "mods list")
    active_mods, inactive_mods = parse_mods_list(mods_text)
    if active_mods:
        raise InputError("active mods unsupported, re-census required: "
                         + ", ".join(active_mods))
    check_no_taxonomy_patch_targets(root, patch_names)
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
        "inventory_items": document["inventory_items"],
        "categories": document["categories"],
        "units_collections_categories": document["units_collections_categories"],
        "stored_items": document["items"],
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
    stored_inventory = layers["inventory_items"]
    stored_categories = layers["categories"]
    stored_collections = layers["units_collections_categories"]
    inventory_keys = list(stored_inventory.keys())
    category_keys = list(stored_categories.keys())
    collection_keys = list(stored_collections.keys())
    problems = []
    inventory_bodies = []
    for key in inventory_keys:
        try:
            inventory_bodies.append(coerce_inventory(stored_inventory[key], key,
                                                     "inventory key " + key))
        except ValidationFailure as failure:
            problems.extend(failure.problems)
    category_bodies = []
    for key in category_keys:
        try:
            category_bodies.append(coerce_category(stored_categories[key], key,
                                                   "category key " + key))
        except ValidationFailure as failure:
            problems.extend(failure.problems)
    collection_bodies = []
    for key in collection_keys:
        try:
            collection_bodies.append(coerce_collection(stored_collections[key],
                                                       key,
                                                       "collection key " + key))
        except ValidationFailure as failure:
            problems.extend(failure.problems)
    if problems:
        raise ValidationFailure(problems)
    if len(set(inventory_keys)) != len(inventory_keys):
        raise ValidationFailure(["duplicate inventory legacy_id"])
    if len(set(category_keys)) != len(category_keys):
        raise ValidationFailure(["duplicate category legacy_id"])
    if len(set(collection_keys)) != len(collection_keys):
        raise ValidationFailure(["duplicate collection legacy_id"])
    inventory = [build_inventory_definition(body, key, fingerprint)
                 for body, key in zip(inventory_bodies, inventory_keys)]
    categories = [build_category_definition(body, key, fingerprint)
                  for body, key in zip(category_bodies, category_keys)]
    collections = [build_collection_definition(body, key, fingerprint)
                   for body, key in zip(collection_bodies, collection_keys)]
    problems.extend(validate_collection_references(collections,
                                                   layers["items_id_set"]))
    problems.extend(validate_inventory_references(layers["stored_items"],
                                                  set(inventory_keys)))
    if problems:
        raise ValidationFailure(problems)
    inventory_schema = load_schema(root, INVENTORY_SCHEMA_FILE.name, "inventory_item")
    category_schema = load_schema(root, CATEGORY_SCHEMA_FILE.name, "category")
    collection_schema = load_schema(root, COLLECTION_SCHEMA_FILE.name,
                                    "unit_collection_category")
    for item in inventory:
        problems.extend(validate_against_schema(
            item, inventory_schema, "inventory_item " + item["legacy_id"]))
    for item in categories:
        problems.extend(validate_against_schema(
            item, category_schema, "category " + item["legacy_id"]))
    for item in collections:
        problems.extend(validate_against_schema(
            item, collection_schema, "unit_collection_category " + item["legacy_id"]))
    if problems:
        raise ValidationFailure(problems)
    ordered_keys = {
        "inventory item": inventory_keys,
        "category": category_keys,
        "collection": collection_keys,
    }
    round_problems = check_round_trip(inventory, categories, collections,
                                      ordered_keys, stored_inventory,
                                      stored_categories, stored_collections)
    if round_problems:
        raise ValidationFailure(round_problems)
    sub_total = sum(len(item["sub"]) for item in categories)
    el_empty = sum(1 for item in collections if not item["category_name_el"])
    costs_null_keys = sorted(item["legacy_id"] for item in collections
                             if item["costs"] is None)
    cat_ids = {item["id"] for item in categories}
    sub_ids = {entry["id"] for item in categories for entry in item["sub"]}
    gap_category = set()
    gap_subcategory = set()
    for entry in layers["stored_items"]:
        if not isinstance(entry, dict):
            continue
        for field, known, gap in (("category_id", cat_ids | sub_ids, gap_category),
                                  ("subcategory_id", cat_ids | sub_ids, gap_subcategory)):
            raw = entry.get(field)
            if isinstance(raw, str) and is_string_encoded_number(raw):
                code = int(float(raw)) if float(raw).is_integer() else raw
                if isinstance(code, int) and code not in known:
                    gap.add(str(code))
    inventory_ids_objects = 0
    inventory_ids_null = 0
    for entry in layers["stored_items"]:
        if not isinstance(entry, dict):
            continue
        if entry.get("inventory_ids") == "null":
            inventory_ids_null += 1
        else:
            inventory_ids_objects += 1
    files = {
        INVENTORY_FILE: inventory,
        CATEGORIES_FILE: categories,
        COLLECTIONS_FILE: collections,
    }
    taxonomy_section = {
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
            "taxonomy_patch_targets": "none",
            "items_reference_edge": {
                "files": [
                    BUILDINGS_FILE.as_posix(),
                    UNITS_FILE.as_posix(),
                    SPECIALS_FILE.as_posix(),
                ],
                "counts": dict(layers["items_counts"]),
                "union_legacy_ids": len(layers["items_id_set"]),
            },
            "inventory_reference_edge": {
                "stored_items": len(layers["stored_items"]),
                "inventory_ids_objects": inventory_ids_objects,
                "inventory_ids_null": inventory_ids_null,
            },
        },
        "coercion_ruleset": COERCION_RULESET_VERSION,
        "content_fingerprint": fingerprint,
        "counts": {
            "stored_inventory": len(stored_inventory),
            "stored_categories": len(stored_categories),
            "stored_collections": len(stored_collections),
            "inventory": len(inventory),
            "categories": len(categories),
            "collections": len(collections),
            "category_sub_total": sub_total,
            "collection_units_total": sum(len(item["units"]) for item in collections),
            "collection_el_empty": el_empty,
            "collection_costs_null_keys": costs_null_keys,
            "gap_category_codes": sorted(gap_category),
            "gap_subcategory_codes": sorted(gap_subcategory),
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
            "Stored taxonomy objects map one-to-one to definitions; "
            "legacy_id is the stored object key verbatim in stored "
            "document order, never re-sorted (rule N2).",
            "Inventory id, cashPrice, droppable, dropRate, and dropsFrom "
            "coerce from string-encoded numbers to integers (rule N1); "
            "names and descriptions are preserved verbatim.",
            "Category ids and names are kept verbatim with sub arrays "
            "carried as observed; every sub parent equals its category "
            "id (rule N3).",
            "Collection native integers are kept verbatim; units "
            "integers resolve against the normalized items legacy-ID "
            "set with unit_refs carried in stored order (rule N3).",
            "Costs is null in exactly one stored entry (key 1); "
            "preserved as null with this note, never defaulted.",
            "category_name_el is empty in every stored entry; preserved "
            "verbatim with this note, never defaulted.",
            "Stored item category/subcategory codes without a category "
            "entry are opaque classification codes with this note "
            "(patch-era units), never treated as references.",
            "Stored items inventory_ids object keys resolve against the "
            "normalized inventory key set; the null string marks "
            "absence (rule N3).",
            "No active patch targets any taxonomy key; the build "
            "refuses patch drift and active mods explicitly.",
        ],
    }
    payloads = {}
    for path, entries in files.items():
        payloads[path] = json.dumps(entries, indent=2) + "\n"
    return taxonomy_section, payloads


def write_outputs(out_root, taxonomy_section, payloads):
    # Byte-exact writes: payloads are encoded once and the same bytes feed
    # the digest records. The taxonomy section is merged into the existing
    # package manifest (items, quests, tables, economy, and social keys
    # preserved); the manifest cannot digest itself, so only the three
    # normalized files are digested.
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
    taxonomy_section["outputs"] = outputs
    manifest_path = out / MANIFEST_FILE
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise InputError("package manifest not object")
    manifest["taxonomy"] = taxonomy_section
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
    taxonomy_section, payloads = build_package(repo_root, out_root)
    manifest = write_outputs(out_root, taxonomy_section, payloads)
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
        "counts": manifest["taxonomy"]["counts"],
        "outputs": [entry["file"] for entry in manifest["taxonomy"]["outputs"]],
        "problems": [],
    }
    print(json.dumps(report, indent=2, sort_keys=True) + "\n", end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
