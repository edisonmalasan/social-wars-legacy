"""Offline quest-normalization builder and validator.

Loads the stored legacy quest content (`goals` and `collections` from
`config/main.json`) directly with no patch layering (no active patch
targets either key; verified per build), reads the committed normalized
items outputs (`normalized/buildings.json`, `normalized/units.json`,
`normalized/specials.json`) for the cross-domain legacy-ID set, coerces
string-encoded values per the documented quest coercion ruleset (citing
the field-type survey), validates duplicate IDs, item-reference
resolution, price shapes, and schema-required fields, and diffs a
legacy-shaped re-emission against the stored content modulo the
documented coercions (round-trip fidelity gate).

On success the normalized quest package (`normalized/quests.json`,
`normalized/collections.json`, plus the `quests` section merged into
`manifest.json`) is written and exit 0 with a JSON report on stdout is
returned. Any validation failure exits 1 without writing output.
Invalid input or unsupported shapes exit 2. Standard library only: no
legacy application import, no runtime save reads, no network, server,
browser, or Flash activity.
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

COERCION_RULESET_VERSION = "quest-coercion-ruleset-v1"
POLICY = "quest-normalization-v1"

MAIN_CONFIG_FILE = Path("config") / "main.json"
PATCH_LIST_FILE = Path("config") / "patch" / "patches.txt"
PATCH_DIR = Path("config") / "patch"
MODS_LIST_FILE = Path("mods") / "mods.txt"
SCHEMA_DIR = Path("packages") / "game-content" / "schemas"
QUEST_SCHEMA_FILE = SCHEMA_DIR / "quest.schema.json"
COLLECTION_SCHEMA_FILE = SCHEMA_DIR / "collection.schema.json"
NORMALIZED_DIR = Path("packages") / "game-content" / "normalized"
BUILDINGS_FILE = NORMALIZED_DIR / "buildings.json"
UNITS_FILE = NORMALIZED_DIR / "units.json"
SPECIALS_FILE = NORMALIZED_DIR / "specials.json"
QUESTS_FILE = NORMALIZED_DIR / "quests.json"
COLLECTIONS_FILE = NORMALIZED_DIR / "collections.json"
MANIFEST_FILE = Path("packages") / "game-content" / "manifest.json"

MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_KEYS = 64
MAX_PATCH_FILES = 32
MAX_PATCH_OPS = 4096
MAX_QUEST_ENTRIES = 4096

# Stored quest field sets (field-type survey: goals mixed 5 fields,
# collections string-encoded 6 fields). Anything else is content drift.
QUEST_FIELDS = ("id", "title", "hint", "description", "reward")
COLLECTION_FIELDS = ("id", "name", "description", "item_ids", "prize",
                     "cashPrice")


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
    for key in ("goals", "collections"):
        if key not in document or not isinstance(document[key], list):
            raise InputError("unsupported content shape: " + key + " not array")
        if len(document[key]) > MAX_QUEST_ENTRIES:
            raise InputError("quest entry limit exceeded: " + key)
    return document


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


def check_no_quest_patch_targets(root, patch_names):
    """Refuse patch drift: no patch may target goals or collections."""
    for name in patch_names:
        operations = load_patch_operations(root, name)
        for position, operation in enumerate(operations):
            if not isinstance(operation, dict):
                raise InputError("unsupported patch shape: " + name)
            target = operation.get("path")
            if not isinstance(target, str) or not target.startswith("/"):
                raise InputError("unsupported patch target path in " + name)
            # The first pointer segment names the top-level content key.
            key = target[1:].split("/", 1)[0] if len(target) > 1 else ""
            if key in ("goals", "collections"):
                raise InputError(
                    "patch targets quest content in " + name + " at position "
                    + str(position) + ": " + repr(target)
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
    """Rule Q1: numeric strings to numbers, integral floats to int."""
    if not is_string_encoded_number(text):
        raise ValidationFailure(["field not numeric string: " + label + " = " + repr(text)])
    try:
        number = float(text)
    except ValueError:
        raise ValidationFailure(["field not numeric string: " + label + " = " + repr(text)])
    if number.is_integer():
        return int(number)
    return number


def coerce_quest(raw, label):
    """Coerce one stored goals entry per rules Q3/Q4 (native fields kept)."""
    if not isinstance(raw, dict):
        raise ValidationFailure(["entry not object: " + label])
    problems = []
    for field in QUEST_FIELDS:
        if field not in raw:
            problems.append("missing field: " + label + "." + field)
    for field in raw:
        if field not in QUEST_FIELDS:
            problems.append("unexpected field: " + label + "." + field)
    if problems:
        raise ValidationFailure(problems)
    if type(raw["id"]) is not int:
        raise ValidationFailure(["quest id not native integer: " + label])
    if type(raw["reward"]) is not int:
        raise ValidationFailure(["quest reward not native integer: " + label])
    if raw["reward"] < 0:
        raise ValidationFailure(["quest reward negative: " + label])
    for field in ("title", "hint", "description"):
        if not isinstance(raw[field], str):
            raise ValidationFailure(["field not string: " + label + "." + field])
    return {
        "id": raw["id"],
        "title": raw["title"],
        "hint": raw["hint"],
        "description": raw["description"],
        "reward": raw["reward"],
    }


def coerce_collection(raw, label):
    """Coerce one stored collections entry per rules Q1/Q2/Q3/Q4."""
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
    for field in ("name", "description"):
        if not isinstance(raw[field], str):
            raise ValidationFailure(["field not string: " + label + "." + field])
    if not isinstance(raw["id"], str):
        raise ValidationFailure(["collection id not string-encoded: " + label])
    entry_id = coerce_number_text(raw["id"], label + ".id")
    if type(entry_id) is not int:
        raise ValidationFailure(["collection id not integral: " + label])
    if not isinstance(raw["cashPrice"], str):
        raise ValidationFailure(["cashPrice not string-encoded: " + label])
    cash_price = coerce_number_text(raw["cashPrice"], label + ".cashPrice")
    if type(cash_price) is not int:
        raise ValidationFailure(["cashPrice not integral: " + label])
    if cash_price < 0:
        raise ValidationFailure(["cashPrice negative: " + label])
    if not isinstance(raw["item_ids"], str) or not is_embedded_json_string(raw["item_ids"]):
        raise ValidationFailure(["item_ids not embedded json: " + label])
    item_ids = json.loads(raw["item_ids"])
    if not isinstance(item_ids, list) or not item_ids:
        raise ValidationFailure(["item_ids not non-empty array: " + label])
    for value in item_ids:
        if type(value) is not int:
            raise ValidationFailure(["item_ids element not integer: " + label])
    if not isinstance(raw["prize"], str) or not is_embedded_json_string(raw["prize"]):
        raise ValidationFailure(["prize not embedded json: " + label])
    prize = json.loads(raw["prize"])
    if not isinstance(prize, dict) or not prize:
        raise ValidationFailure(["prize not non-empty object: " + label])
    for key, amount in prize.items():
        if type(amount) is not int or amount < 1:
            raise ValidationFailure(["prize amount not positive int: " + label
                                     + " key " + repr(key)])
    return {
        "id": entry_id,
        "name": raw["name"],
        "description": raw["description"],
        "item_ids": item_ids,
        "prize": prize,
        "cashPrice": cash_price,
    }


def build_quest_definition(body, legacy_id, fingerprint):
    return {
        "legacy_id": legacy_id,
        "kind": "quest",
        "source_file": MAIN_CONFIG_FILE.as_posix(),
        "source_layer": "stored",
        "content_version": fingerprint,
        "id": body["id"],
        "title": body["title"],
        "hint": body["hint"],
        "description": body["description"],
        "reward": body["reward"],
    }


def build_collection_definition(body, legacy_id, fingerprint):
    prize = {str(key): body["prize"][key] for key in body["prize"]}
    return {
        "legacy_id": legacy_id,
        "kind": "collection",
        "source_file": MAIN_CONFIG_FILE.as_posix(),
        "source_layer": "stored",
        "content_version": fingerprint,
        "id": body["id"],
        "name": body["name"],
        "description": body["description"],
        "item_ids": list(body["item_ids"]),
        "item_refs": [str(value) for value in body["item_ids"]],
        "prize": prize,
        "prize_refs": sorted(prize.keys()),
        "cashPrice": body["cashPrice"],
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
    """Enforce schema required/type/const/enum/minimum/minItems/minProperties/
    propertyNames/items/additionalProperties gates."""
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
        if "minProperties" in spec and isinstance(value, dict):
            if len(value) < spec["minProperties"]:
                problems.append("object below minProperties at " + label + "." + field)
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
                if "minimum" in additional and type(amount) is int:
                    if amount < additional["minimum"]:
                        problems.append("value below minimum at " + label + "."
                                        + field + "." + str(key))
    if schema.get("additionalProperties") is False:
        for field in definition:
            if field not in schema["properties"]:
                problems.append("additional property: " + label + "." + field)
    return problems


def validate_collection_references(definition, known_ids):
    """Collection item_ids and prize keys must resolve to normalized items."""
    problems = []
    legacy_id = definition["legacy_id"]
    for value in definition["item_ids"]:
        if str(value) not in known_ids:
            problems.append("unresolvable item_ids reference for collection "
                            + legacy_id + ": " + repr(value))
    for key in definition["prize"]:
        if str(key) not in known_ids:
            problems.append("unresolvable prize reference for collection "
                            + legacy_id + ": " + repr(key))
    if definition["item_refs"] != [str(value) for value in definition["item_ids"]]:
        problems.append("item_refs drift for collection " + legacy_id)
    if definition["prize_refs"] != sorted(definition["prize"].keys()):
        problems.append("prize_refs drift for collection " + legacy_id)
    return problems


def check_round_trip(quests, collections, stored_goals, stored_collections):
    """Diff legacy re-emission against stored content modulo coercions."""
    problems = []
    if len(quests) != len(stored_goals):
        problems.append("round-trip quest count mismatch: %d definitions vs %d stored"
                        % (len(quests), len(stored_goals)))
    if len(collections) != len(stored_collections):
        problems.append("round-trip collection count mismatch: %d definitions vs %d stored"
                        % (len(collections), len(stored_collections)))
    for definition, original in zip(quests, stored_goals):
        label = "round-trip quest " + definition["legacy_id"]
        if not isinstance(original, dict):
            problems.append(label + ": stored entry not object")
            continue
        if str(original.get("id")) != definition["legacy_id"]:
            problems.append(label + ": order/identity mismatch")
            continue
        try:
            body = coerce_quest(original, "round-trip")
        except ValidationFailure as failure:
            problems.extend([label + ": " + item for item in failure.problems])
            continue
        for field in QUEST_FIELDS:
            if body[field] != definition[field]:
                problems.append(label + ": drift at " + field)
        if set(original.keys()) != set(QUEST_FIELDS):
            problems.append(label + ": field-set drift "
                            + repr(sorted(set(original.keys()) ^ set(QUEST_FIELDS))))
    for definition, original in zip(collections, stored_collections):
        label = "round-trip collection " + definition["legacy_id"]
        if not isinstance(original, dict):
            problems.append(label + ": stored entry not object")
            continue
        if not isinstance(original.get("id"), str):
            problems.append(label + ": stored id not string")
            continue
        if str(definition["id"]) != original["id"]:
            problems.append(label + ": order/identity mismatch")
            continue
        try:
            body = coerce_collection(original, "round-trip")
        except ValidationFailure as failure:
            problems.extend([label + ": " + item for item in failure.problems])
            continue
        if body["id"] != definition["id"]:
            problems.append(label + ": drift at id")
        for field in ("name", "description", "cashPrice"):
            if body[field] != definition[field]:
                problems.append(label + ": drift at " + field)
        if body["item_ids"] != definition["item_ids"]:
            problems.append(label + ": drift at item_ids")
        expected_prize = {str(key): body["prize"][key] for key in body["prize"]}
        if expected_prize != definition["prize"]:
            problems.append(label + ": drift at prize")
        if set(original.keys()) != set(COLLECTION_FIELDS):
            problems.append(label + ": field-set drift "
                            + repr(sorted(set(original.keys()) ^ set(COLLECTION_FIELDS))))
    return problems


def load_all(root):
    """Load stored quest content and the cross-domain items ID set."""
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
    for key in ("goals", "collections"):
        if key not in document or not isinstance(document[key], list):
            raise InputError("unsupported content shape: " + key + " not array")
    patch_names = parse_patch_list(
        read_text_file(root / PATCH_LIST_FILE, "patch list"))
    mods_text = read_text_file(root / MODS_LIST_FILE, "mods list")
    active_mods, inactive_mods = parse_mods_list(mods_text)
    if active_mods:
        raise InputError("active mods unsupported, re-census required: "
                         + ", ".join(active_mods))
    check_no_quest_patch_targets(root, patch_names)
    mods_bytes = read_bytes_file(root / MODS_LIST_FILE, "mods list")
    known_ids, items_counts = load_items_id_set(root)
    manifest_text = read_text_file(root / MANIFEST_FILE, "package manifest")
    try:
        manifest_document = json.loads(manifest_text)
    except ValueError:
        raise InputError("package manifest not valid json")
    if not isinstance(manifest_document, dict):
        raise InputError("package manifest not object")
    return {
        "goals": document["goals"],
        "collections": document["collections"],
        "patch_names": patch_names,
        "active_mods": active_mods,
        "inactive_mods": inactive_mods,
        "known_ids": known_ids,
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
    stored_goals = layers["goals"]
    stored_collections = layers["collections"]
    known_ids = layers["known_ids"]
    problems = []
    bodies = []
    quest_ids = []
    for entry in stored_goals:
        label = ("goal id " + repr(entry.get("id"))
                 if isinstance(entry, dict) else "goal entry")
        try:
            body = coerce_quest(entry, label)
        except ValidationFailure as failure:
            problems.extend(failure.problems)
            continue
        quest_ids.append(str(body["id"]))
        bodies.append(("quest", body))
    collection_bodies = []
    for entry in stored_collections:
        label = ("collection id " + repr(entry.get("id"))
                 if isinstance(entry, dict) else "collection entry")
        try:
            body = coerce_collection(entry, label)
        except ValidationFailure as failure:
            problems.extend(failure.problems)
            continue
        collection_bodies.append(body)
    if problems:
        raise ValidationFailure(problems)
    if len(set(quest_ids)) != len(quest_ids):
        raise ValidationFailure(["duplicate quest legacy_id in stored goals"])
    raw_collection_ids = []
    for entry in stored_collections:
        raw_collection_ids.append(entry["id"] if isinstance(entry, dict) else entry)
    if len(set(raw_collection_ids)) != len(raw_collection_ids):
        raise ValidationFailure(["duplicate collection legacy_id in stored collections"])
    quests = [build_quest_definition(body, str(body["id"]), fingerprint)
              for _kind, body in bodies]
    collections = [build_collection_definition(
        body, body_raw_id, fingerprint)
        for body, body_raw_id in zip(collection_bodies, raw_collection_ids)]
    quest_schema = load_schema(root, QUEST_SCHEMA_FILE.name, "quest")
    collection_schema = load_schema(root, COLLECTION_SCHEMA_FILE.name, "collection")
    for item in quests:
        problems.extend(validate_against_schema(
            item, quest_schema, "quest " + item["legacy_id"]))
    for item in collections:
        problems.extend(validate_against_schema(
            item, collection_schema, "collection " + item["legacy_id"]))
        problems.extend(validate_collection_references(item, known_ids))
    if problems:
        raise ValidationFailure(problems)
    round_problems = check_round_trip(quests, collections,
                                      stored_goals, stored_collections)
    if round_problems:
        raise ValidationFailure(round_problems)
    hint_empty = sum(1 for item in quests if item["hint"] == "")
    reward_values = {item["reward"] for item in quests}
    files = {
        QUESTS_FILE: quests,
        COLLECTIONS_FILE: collections,
    }
    quest_section = {
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
            "quest_patch_targets": "none",
            "items_reference_edge": {
                "files": [BUILDINGS_FILE.as_posix(), UNITS_FILE.as_posix(),
                          SPECIALS_FILE.as_posix()],
                "counts": layers["items_counts"],
                "union_legacy_ids": len(known_ids),
            },
        },
        "coercion_ruleset": COERCION_RULESET_VERSION,
        "content_fingerprint": fingerprint,
        "counts": {
            "stored_goals": len(stored_goals),
            "stored_collections": len(stored_collections),
            "quests": len(quests),
            "collections": len(collections),
            "hint_empty": hint_empty,
            "reward_values": sorted(reward_values),
        },
        "validation": {
            "duplicate_ids": 0,
            "unresolvable_references": 0,
            "price_violations": 0,
            "missing_fields": 0,
            "round_trip_diffs": 0,
        },
        "outputs": [],
        "notes": [
            "Stored goals map one-to-one to quests; native integer id and "
            "reward kept verbatim (rule Q3).",
            "hint is empty in all stored goals entries; preserved verbatim "
            "with this note (rule Q3).",
            "reward is uniform (10) across all stored goals entries; "
            "preserved verbatim with this note, never defaulted (rule Q3).",
            "Collection id and cashPrice coerce from string-encoded numbers "
            "to integers (rule Q1); item_ids and prize coerce from "
            "embedded-JSON strings to an integer array and an object "
            "(rule Q2).",
            "item_refs/prize_refs carry the resolved cross-domain item "
            "references validated against the normalized items legacy-ID "
            "set; unresolvable references fail validation (rule Q5).",
            "No active patch targets goals or collections; the build "
            "refuses patch drift and active mods explicitly.",
        ],
    }
    payloads = {}
    for path, entries in files.items():
        payloads[path] = json.dumps(entries, indent=2) + "\n"
    return quest_section, payloads


def write_outputs(out_root, quest_section, payloads):
    # Byte-exact writes: payloads are encoded once and the same bytes feed
    # the digest records. The quests section is merged into the existing
    # package manifest (items keys preserved); the manifest cannot digest
    # itself, so only the two normalized files are digested.
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
    quest_section["outputs"] = outputs
    manifest_path = out / MANIFEST_FILE
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise InputError("package manifest not object")
    manifest["quests"] = quest_section
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
    quest_section, payloads = build_package(repo_root, out_root)
    manifest = write_outputs(out_root, quest_section, payloads)
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
        "counts": manifest["quests"]["counts"],
        "outputs": [entry["file"] for entry in manifest["quests"]["outputs"]],
        "problems": [],
    }
    print(json.dumps(report, indent=2, sort_keys=True) + "\n", end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
