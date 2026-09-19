"""Offline reference-tables normalization builder and validator.

Loads the stored legacy reference tables (`magics`, `levels`, and `sounds`
from `config/main.json`) directly with no patch layering (no active patch
targets any of the three keys; verified per build), coerces string-encoded
values per the documented tables coercion ruleset (citing the field-type
survey), validates duplicate IDs, non-negative amounts, and schema-required
fields, and diffs a legacy-shaped re-emission against the stored content
modulo the documented coercions (round-trip fidelity gate). The XP curve
order is positional and preserved; asset names are recorded, never
validated.

On success the normalized tables package (`normalized/magics.json`,
`normalized/levels.json`, `normalized/sounds.json`, plus the `tables`
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

COERCION_RULESET_VERSION = "tables-coercion-ruleset-v1"
POLICY = "tables-normalization-v1"

MAIN_CONFIG_FILE = Path("config") / "main.json"
PATCH_LIST_FILE = Path("config") / "patch" / "patches.txt"
PATCH_DIR = Path("config") / "patch"
MODS_LIST_FILE = Path("mods") / "mods.txt"
SCHEMA_DIR = Path("packages") / "game-content" / "schemas"
MAGIC_SCHEMA_FILE = SCHEMA_DIR / "magic.schema.json"
LEVEL_SCHEMA_FILE = SCHEMA_DIR / "level.schema.json"
SOUND_SCHEMA_FILE = SCHEMA_DIR / "sound.schema.json"
NORMALIZED_DIR = Path("packages") / "game-content" / "normalized"
MAGICS_FILE = NORMALIZED_DIR / "magics.json"
LEVELS_FILE = NORMALIZED_DIR / "levels.json"
SOUNDS_FILE = NORMALIZED_DIR / "sounds.json"
MANIFEST_FILE = Path("packages") / "game-content" / "manifest.json"

MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_KEYS = 64
MAX_PATCH_FILES = 32
MAX_PATCH_OPS = 4096
MAX_TABLE_ENTRIES = 4096

# Stored table field sets (field-type survey: magics mixed 10 fields with an
# embedded-JSON area array string; levels mixed 4 fully-native fields with no
# stable id; sounds string-encoded 6 fields). Anything else is content drift.
MAGIC_FIELDS = ("id", "name", "description", "mana", "level", "gold", "cash",
                "target", "area", "img_name")
LEVEL_FIELDS = ("name", "exp_required", "reward_type", "reward_amount")
SOUND_FIELDS = ("id", "file", "max", "loops", "preload", "description")

# Native integer amount fields that must be non-negative (rule T3).
MAGIC_AMOUNTS = ("mana", "level", "gold", "cash", "target")
SOUND_AMOUNTS = ("loops", "max", "preload")

TABLE_KEYS = ("magics", "levels", "sounds")


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
    for key in TABLE_KEYS:
        if key not in document or not isinstance(document[key], list):
            raise InputError("unsupported content shape: " + key + " not array")
        if len(document[key]) > MAX_TABLE_ENTRIES:
            raise InputError("table entry limit exceeded: " + key)
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


def check_no_tables_patch_targets(root, patch_names):
    """Refuse patch drift: no patch may target magics, levels, or sounds."""
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
            if key in TABLE_KEYS:
                raise InputError(
                    "patch targets reference-table content in " + name
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


def coerce_number_text(text, label):
    """Rule T1: numeric strings to numbers, integral floats to int."""
    if not is_string_encoded_number(text):
        raise ValidationFailure(["field not numeric string: " + label + " = " + repr(text)])
    try:
        number = float(text)
    except ValueError:
        raise ValidationFailure(["field not numeric string: " + label + " = " + repr(text)])
    if number.is_integer():
        return int(number)
    return number


def coerce_magic(raw, label):
    """Coerce one stored magics entry per rules T2/T3 (native kept, area parsed)."""
    if not isinstance(raw, dict):
        raise ValidationFailure(["entry not object: " + label])
    problems = []
    for field in MAGIC_FIELDS:
        if field not in raw:
            problems.append("missing field: " + label + "." + field)
    for field in raw:
        if field not in MAGIC_FIELDS:
            problems.append("unexpected field: " + label + "." + field)
    if problems:
        raise ValidationFailure(problems)
    if type(raw["id"]) is not int:
        raise ValidationFailure(["magic id not native integer: " + label])
    for field in MAGIC_AMOUNTS:
        if type(raw[field]) is not int:
            raise ValidationFailure(["field not native integer: " + label + "." + field])
        if raw[field] < 0:
            raise ValidationFailure(["field negative: " + label + "." + field])
    for field in ("name", "description", "img_name"):
        if not isinstance(raw[field], str):
            raise ValidationFailure(["field not string: " + label + "." + field])
    if not isinstance(raw["area"], str) or not is_embedded_json_string(raw["area"]):
        raise ValidationFailure(["area not embedded json: " + label])
    area = json.loads(raw["area"])
    if not isinstance(area, list) or not area:
        raise ValidationFailure(["area not non-empty array: " + label])
    for value in area:
        if type(value) is not int:
            raise ValidationFailure(["area element not integer: " + label])
    return {
        "id": raw["id"],
        "name": raw["name"],
        "description": raw["description"],
        "mana": raw["mana"],
        "level": raw["level"],
        "gold": raw["gold"],
        "cash": raw["cash"],
        "target": raw["target"],
        "area": area,
        "img_name": raw["img_name"],
    }


def coerce_level(raw, index, label):
    """Coerce one stored levels entry per rule T3 (fully native, kept verbatim)."""
    if not isinstance(raw, dict):
        raise ValidationFailure(["entry not object: " + label])
    problems = []
    for field in LEVEL_FIELDS:
        if field not in raw:
            problems.append("missing field: " + label + "." + field)
    for field in raw:
        if field not in LEVEL_FIELDS:
            problems.append("unexpected field: " + label + "." + field)
    if problems:
        raise ValidationFailure(problems)
    if not isinstance(raw["name"], str):
        raise ValidationFailure(["field not string: " + label + ".name"])
    if type(raw["exp_required"]) is not int:
        raise ValidationFailure(["exp_required not native integer: " + label])
    if raw["exp_required"] < 0:
        raise ValidationFailure(["exp_required negative: " + label])
    if not isinstance(raw["reward_type"], str):
        raise ValidationFailure(["reward_type not string: " + label])
    if type(raw["reward_amount"]) is not int:
        raise ValidationFailure(["reward_amount not native integer: " + label])
    if raw["reward_amount"] < 0:
        raise ValidationFailure(["reward_amount negative: " + label])
    return {
        "level_index": index,
        "name": raw["name"],
        "exp_required": raw["exp_required"],
        "reward_type": raw["reward_type"],
        "reward_amount": raw["reward_amount"],
    }


def coerce_sound(raw, label):
    """Coerce one stored sounds entry per rules T1/T3 (numerics parsed, assets verbatim)."""
    if not isinstance(raw, dict):
        raise ValidationFailure(["entry not object: " + label])
    problems = []
    for field in SOUND_FIELDS:
        if field not in raw:
            problems.append("missing field: " + label + "." + field)
    for field in raw:
        if field not in SOUND_FIELDS:
            problems.append("unexpected field: " + label + "." + field)
    if problems:
        raise ValidationFailure(problems)
    for field in ("file", "description"):
        if not isinstance(raw[field], str):
            raise ValidationFailure(["field not string: " + label + "." + field])
    if not isinstance(raw["id"], str):
        raise ValidationFailure(["sound id not string-encoded: " + label])
    entry_id = coerce_number_text(raw["id"], label + ".id")
    if type(entry_id) is not int:
        raise ValidationFailure(["sound id not integral: " + label])
    amounts = {}
    for field in SOUND_AMOUNTS:
        if not isinstance(raw[field], str):
            raise ValidationFailure([field + " not string-encoded: " + label])
        value = coerce_number_text(raw[field], label + "." + field)
        if type(value) is not int:
            raise ValidationFailure([field + " not integral: " + label])
        if value < 0:
            raise ValidationFailure([field + " negative: " + label])
        amounts[field] = value
    return {
        "id": entry_id,
        "file": raw["file"],
        "description": raw["description"],
        "loops": amounts["loops"],
        "max": amounts["max"],
        "preload": amounts["preload"],
    }


def build_magic_definition(body, fingerprint):
    return {
        "legacy_id": str(body["id"]),
        "kind": "magic",
        "source_file": MAIN_CONFIG_FILE.as_posix(),
        "source_layer": "stored",
        "content_version": fingerprint,
        "id": body["id"],
        "name": body["name"],
        "description": body["description"],
        "mana": body["mana"],
        "level": body["level"],
        "gold": body["gold"],
        "cash": body["cash"],
        "target": body["target"],
        "area": list(body["area"]),
        "img_name": body["img_name"],
    }


def build_level_definition(body, fingerprint):
    return {
        "legacy_id": str(body["level_index"]),
        "kind": "level",
        "source_file": MAIN_CONFIG_FILE.as_posix(),
        "source_layer": "stored",
        "content_version": fingerprint,
        "level_index": body["level_index"],
        "name": body["name"],
        "exp_required": body["exp_required"],
        "reward_type": body["reward_type"],
        "reward_amount": body["reward_amount"],
    }


def build_sound_definition(body, legacy_id, fingerprint):
    return {
        "legacy_id": legacy_id,
        "kind": "sound",
        "source_file": MAIN_CONFIG_FILE.as_posix(),
        "source_layer": "stored",
        "content_version": fingerprint,
        "id": body["id"],
        "file": body["file"],
        "description": body["description"],
        "loops": body["loops"],
        "max": body["max"],
        "preload": body["preload"],
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


def check_round_trip(magics, levels, sounds,
                     stored_magics, stored_levels, stored_sounds):
    """Diff legacy re-emission against stored content modulo coercions."""
    problems = []
    if len(magics) != len(stored_magics):
        problems.append("round-trip magic count mismatch: %d definitions vs %d stored"
                        % (len(magics), len(stored_magics)))
    if len(levels) != len(stored_levels):
        problems.append("round-trip level count mismatch: %d definitions vs %d stored"
                        % (len(levels), len(stored_levels)))
    if len(sounds) != len(stored_sounds):
        problems.append("round-trip sound count mismatch: %d definitions vs %d stored"
                        % (len(sounds), len(stored_sounds)))
    for definition, original in zip(magics, stored_magics):
        label = "round-trip magic " + definition["legacy_id"]
        if not isinstance(original, dict):
            problems.append(label + ": stored entry not object")
            continue
        if str(original.get("id")) != definition["legacy_id"]:
            problems.append(label + ": order/identity mismatch")
            continue
        try:
            body = coerce_magic(original, "round-trip")
        except ValidationFailure as failure:
            problems.extend([label + ": " + item for item in failure.problems])
            continue
        for field in ("id", "name", "description", "mana", "level",
                      "gold", "cash", "target", "img_name"):
            if body[field] != definition[field]:
                problems.append(label + ": drift at " + field)
        if body["area"] != definition["area"]:
            problems.append(label + ": drift at area")
        if set(original.keys()) != set(MAGIC_FIELDS):
            problems.append(label + ": field-set drift "
                            + repr(sorted(set(original.keys()) ^ set(MAGIC_FIELDS))))
    for position, (definition, original) in enumerate(zip(levels, stored_levels)):
        label = "round-trip level " + definition["legacy_id"]
        if not isinstance(original, dict):
            problems.append(label + ": stored entry not object")
            continue
        # Levels have no stored id: identity is positional.
        if definition["legacy_id"] != str(position):
            problems.append(label + ": order/identity mismatch")
            continue
        try:
            body = coerce_level(original, position, "round-trip")
        except ValidationFailure as failure:
            problems.extend([label + ": " + item for item in failure.problems])
            continue
        for field in ("name", "exp_required", "reward_type", "reward_amount"):
            if body[field] != definition[field]:
                problems.append(label + ": drift at " + field)
        if body["level_index"] != definition["level_index"]:
            problems.append(label + ": drift at level_index")
        if set(original.keys()) != set(LEVEL_FIELDS):
            problems.append(label + ": field-set drift "
                            + repr(sorted(set(original.keys()) ^ set(LEVEL_FIELDS))))
    for definition, original in zip(sounds, stored_sounds):
        label = "round-trip sound " + definition["legacy_id"]
        if not isinstance(original, dict):
            problems.append(label + ": stored entry not object")
            continue
        if not isinstance(original.get("id"), str):
            problems.append(label + ": stored id not string")
            continue
        if original["id"] != definition["legacy_id"]:
            problems.append(label + ": order/identity mismatch")
            continue
        try:
            body = coerce_sound(original, "round-trip")
        except ValidationFailure as failure:
            problems.extend([label + ": " + item for item in failure.problems])
            continue
        if body["id"] != definition["id"]:
            problems.append(label + ": drift at id")
        for field in ("file", "description", "loops", "max", "preload"):
            if body[field] != definition[field]:
                problems.append(label + ": drift at " + field)
        if set(original.keys()) != set(SOUND_FIELDS):
            problems.append(label + ": field-set drift "
                            + repr(sorted(set(original.keys()) ^ set(SOUND_FIELDS))))
    return problems


def load_all(root):
    """Load the stored reference tables with patch-drift and mod guards."""
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
    for key in TABLE_KEYS:
        if key not in document or not isinstance(document[key], list):
            raise InputError("unsupported content shape: " + key + " not array")
    patch_names = parse_patch_list(
        read_text_file(root / PATCH_LIST_FILE, "patch list"))
    mods_text = read_text_file(root / MODS_LIST_FILE, "mods list")
    active_mods, inactive_mods = parse_mods_list(mods_text)
    if active_mods:
        raise InputError("active mods unsupported, re-census required: "
                         + ", ".join(active_mods))
    check_no_tables_patch_targets(root, patch_names)
    mods_bytes = read_bytes_file(root / MODS_LIST_FILE, "mods list")
    manifest_text = read_text_file(root / MANIFEST_FILE, "package manifest")
    try:
        manifest_document = json.loads(manifest_text)
    except ValueError:
        raise InputError("package manifest not valid json")
    if not isinstance(manifest_document, dict):
        raise InputError("package manifest not object")
    return {
        "magics": document["magics"],
        "levels": document["levels"],
        "sounds": document["sounds"],
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
    stored_magics = layers["magics"]
    stored_levels = layers["levels"]
    stored_sounds = layers["sounds"]
    problems = []
    magic_bodies = []
    for entry in stored_magics:
        label = ("magic id " + repr(entry.get("id"))
                 if isinstance(entry, dict) else "magic entry")
        try:
            magic_bodies.append(coerce_magic(entry, label))
        except ValidationFailure as failure:
            problems.extend(failure.problems)
    level_bodies = []
    for position, entry in enumerate(stored_levels):
        try:
            level_bodies.append(coerce_level(entry, position,
                                             "level index " + str(position)))
        except ValidationFailure as failure:
            problems.extend(failure.problems)
    sound_bodies = []
    raw_sound_ids = []
    for entry in stored_sounds:
        label = ("sound id " + repr(entry.get("id"))
                 if isinstance(entry, dict) else "sound entry")
        try:
            sound_bodies.append(coerce_sound(entry, label))
        except ValidationFailure as failure:
            problems.extend(failure.problems)
            continue
        raw_sound_ids.append(entry["id"] if isinstance(entry, dict) else entry)
    if problems:
        raise ValidationFailure(problems)
    magic_ids = [str(body["id"]) for body in magic_bodies]
    if len(set(magic_ids)) != len(magic_ids):
        raise ValidationFailure(["duplicate magic legacy_id in stored magics"])
    if len(set(raw_sound_ids)) != len(raw_sound_ids):
        raise ValidationFailure(["duplicate sound legacy_id in stored sounds"])
    magics = [build_magic_definition(body, fingerprint)
              for body in magic_bodies]
    levels = [build_level_definition(body, fingerprint)
              for body in level_bodies]
    sounds = [build_sound_definition(body, legacy_id, fingerprint)
              for body, legacy_id in zip(sound_bodies, raw_sound_ids)]
    magic_schema = load_schema(root, MAGIC_SCHEMA_FILE.name, "magic")
    level_schema = load_schema(root, LEVEL_SCHEMA_FILE.name, "level")
    sound_schema = load_schema(root, SOUND_SCHEMA_FILE.name, "sound")
    for item in magics:
        problems.extend(validate_against_schema(
            item, magic_schema, "magic " + item["legacy_id"]))
    for item in levels:
        problems.extend(validate_against_schema(
            item, level_schema, "level " + item["legacy_id"]))
    for item in sounds:
        problems.extend(validate_against_schema(
            item, sound_schema, "sound " + item["legacy_id"]))
    if problems:
        raise ValidationFailure(problems)
    round_problems = check_round_trip(magics, levels, sounds,
                                      stored_magics, stored_levels,
                                      stored_sounds)
    if round_problems:
        raise ValidationFailure(round_problems)
    exp_values = [item["exp_required"] for item in levels]
    exp_monotonic = all(later >= earlier
                        for earlier, later in zip(exp_values, exp_values[1:]))
    reward_types = sorted({item["reward_type"] for item in levels})
    files = {
        MAGICS_FILE: magics,
        LEVELS_FILE: levels,
        SOUNDS_FILE: sounds,
    }
    tables_section = {
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
            "tables_patch_targets": "none",
        },
        "coercion_ruleset": COERCION_RULESET_VERSION,
        "content_fingerprint": fingerprint,
        "counts": {
            "stored_magics": len(stored_magics),
            "stored_levels": len(stored_levels),
            "stored_sounds": len(stored_sounds),
            "magics": len(magics),
            "levels": len(levels),
            "sounds": len(sounds),
            "exp_min": min(exp_values),
            "exp_max": max(exp_values),
            "exp_monotonic_nondecreasing": exp_monotonic,
            "reward_types": reward_types,
        },
        "validation": {
            "duplicate_ids": 0,
            "amount_violations": 0,
            "missing_fields": 0,
            "round_trip_diffs": 0,
        },
        "outputs": [],
        "notes": [
            "Stored magics map one-to-one to magics; native integer id "
            "and mana/level/gold/cash/target kept verbatim (rule T3).",
            "Magic area coerces from the embedded-JSON string to a "
            "non-empty integer array (rule T2); offsets are formation "
            "data, never item references.",
            "Levels carry no stable stored id; legacy_id is the 0-based "
            "positional index as a string and level_index preserves the "
            "XP curve order positionally (rule T4), matching the legacy "
            "positional loader.",
            "Stored levels map one-to-one to levels; all native fields "
            "kept verbatim including any curve irregularities, never "
            "smoothed (rule T3).",
            "Sound id, loops, max, and preload coerce from "
            "string-encoded numbers to integers (rule T1).",
            "img_name, file, and description strings are recorded "
            "verbatim and never validated; asset truth belongs to M4 "
            "(rule T3).",
            "No active patch targets magics, levels, or sounds; the "
            "build refuses patch drift and active mods explicitly.",
        ],
    }
    payloads = {}
    for path, entries in files.items():
        payloads[path] = json.dumps(entries, indent=2) + "\n"
    return tables_section, payloads


def write_outputs(out_root, tables_section, payloads):
    # Byte-exact writes: payloads are encoded once and the same bytes feed
    # the digest records. The tables section is merged into the existing
    # package manifest (items and quests keys preserved); the manifest
    # cannot digest itself, so only the three normalized files are digested.
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
    tables_section["outputs"] = outputs
    manifest_path = out / MANIFEST_FILE
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise InputError("package manifest not object")
    manifest["tables"] = tables_section
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
    tables_section, payloads = build_package(repo_root, out_root)
    manifest = write_outputs(out_root, tables_section, payloads)
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
        "counts": manifest["tables"]["counts"],
        "outputs": [entry["file"] for entry in manifest["tables"]["outputs"]],
        "problems": [],
    }
    print(json.dumps(report, indent=2, sort_keys=True) + "\n", end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
