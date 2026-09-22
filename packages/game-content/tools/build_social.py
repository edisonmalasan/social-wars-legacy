"""Offline social-tables normalization builder and validator.

Loads the stored legacy social tables (`neighbor_assists`, `findable_items`,
and `social_items` from `config/main.json`) directly with no patch layering
(no active patch targets any of the three keys; verified per build), keeps
every native amount and display string verbatim per the documented social
coercion ruleset (citing the field-type survey), validates positional/id
uniqueness, non-negative amounts, and schema-required fields, and diffs a
legacy-shaped re-emission against the stored content exactly (round-trip
fidelity gate). Entry order is positional and preserved; uniform values
(identical assist rewards, uniform findable coins, uniformly-empty social
descriptions) are carried verbatim with manifest notes, never factored out.

On success the normalized social package (`normalized/neighbor_assists.json`,
`normalized/findable_items.json`, `normalized/social_items.json`, plus the
`social` section merged into `manifest.json`) is written and exit 0 with a
JSON report on stdout is returned. Any validation failure exits 1 without
writing output. Invalid input or unsupported shapes exit 2. Standard library
only: no legacy application import, no runtime save reads, no network,
server, browser, or Flash activity.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys

COERCION_RULESET_VERSION = "social-coercion-ruleset-v1"
POLICY = "social-normalization-v1"

MAIN_CONFIG_FILE = Path("config") / "main.json"
PATCH_LIST_FILE = Path("config") / "patch" / "patches.txt"
PATCH_DIR = Path("config") / "patch"
MODS_LIST_FILE = Path("mods") / "mods.txt"
SCHEMA_DIR = Path("packages") / "game-content" / "schemas"
ASSIST_SCHEMA_FILE = SCHEMA_DIR / "neighbor_assist.schema.json"
FINDABLE_SCHEMA_FILE = SCHEMA_DIR / "findable_item.schema.json"
SOCIAL_SCHEMA_FILE = SCHEMA_DIR / "social_item.schema.json"
NORMALIZED_DIR = Path("packages") / "game-content" / "normalized"
ASSISTS_FILE = NORMALIZED_DIR / "neighbor_assists.json"
FINDABLES_FILE = NORMALIZED_DIR / "findable_items.json"
SOCIAL_FILE = NORMALIZED_DIR / "social_items.json"
MANIFEST_FILE = Path("packages") / "game-content" / "manifest.json"

MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_KEYS = 64
MAX_PATCH_FILES = 32
MAX_PATCH_OPS = 4096
MAX_TABLE_ENTRIES = 4096

# Stored table field sets (field-type survey: neighbor_assists mixed with a
# reward object plus rnd number and display strings; findable_items mixed
# with native id/coins plus display strings; social_items mixed with native
# id/worker_cost plus display strings). Anything else is content drift.
ASSIST_FIELDS = ("action", "notification", "reward", "rnd", "task")
REWARD_FIELDS = ("coins", "cash", "xp")
FINDABLE_FIELDS = ("coins", "description", "id", "title")
SOCIAL_FIELDS = ("description", "id", "worker_cost", "workers")

SOCIAL_KEYS = ("neighbor_assists", "findable_items", "social_items")


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


def check_no_social_patch_targets(root, patch_names):
    """Refuse patch drift: no patch may target the three social keys."""
    for name in patch_names:
        operations = load_patch_operations(root, name)
        for position, operation in enumerate(operations):
            if not isinstance(operation, dict):
                raise InputError("unsupported patch shape: " + name)
            target = operation.get("path")
            if not isinstance(target, str) or not target.startswith("/"):
                raise InputError("unsupported patch target path in " + name)
            key = target[1:].split("/", 1)[0] if len(target) > 1 else ""
            if key in SOCIAL_KEYS:
                raise InputError(
                    "patch targets social-table content in " + name
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


def require_native_amount(value, label):
    """Rule S1: schedule amounts are native integers, never booleans."""
    if type(value) is not int:
        raise ValidationFailure(["field not native integer: " + label])
    if value < 0:
        raise ValidationFailure(["field negative: " + label])
    return value


def coerce_assist(raw, position, label):
    """Coerce one stored neighbor_assists entry per rule S1 (verbatim)."""
    if not isinstance(raw, dict):
        raise ValidationFailure(["entry not object: " + label])
    problems = []
    for field in ASSIST_FIELDS:
        if field not in raw:
            problems.append("missing field: " + label + "." + field)
    for field in raw:
        if field not in ASSIST_FIELDS:
            problems.append("unexpected field: " + label + "." + field)
    if problems:
        raise ValidationFailure(problems)
    for field in ("task", "action", "notification"):
        if not isinstance(raw[field], str):
            raise ValidationFailure(["field not string: " + label + "." + field])
    try:
        rnd = require_native_amount(raw["rnd"], label + ".rnd")
    except ValidationFailure as failure:
        raise ValidationFailure(failure.problems)
    reward = raw["reward"]
    if not isinstance(reward, dict):
        raise ValidationFailure(["reward not object: " + label])
    reward_problems = []
    for field in REWARD_FIELDS:
        if field not in reward:
            reward_problems.append("missing field: " + label + ".reward." + field)
    for field in reward:
        if field not in REWARD_FIELDS:
            reward_problems.append("unexpected field: " + label + ".reward." + field)
    if reward_problems:
        raise ValidationFailure(reward_problems)
    amounts = {}
    for field in REWARD_FIELDS:
        try:
            amounts[field] = require_native_amount(reward[field],
                                                   label + ".reward." + field)
        except ValidationFailure as failure:
            raise ValidationFailure(failure.problems)
    return {
        "position": position,
        "task": raw["task"],
        "action": raw["action"],
        "notification": raw["notification"],
        "rnd": rnd,
        "reward": amounts,
    }


def coerce_findable(raw, label):
    """Coerce one stored findable_items entry per rule S1 (verbatim)."""
    if not isinstance(raw, dict):
        raise ValidationFailure(["entry not object: " + label])
    problems = []
    for field in FINDABLE_FIELDS:
        if field not in raw:
            problems.append("missing field: " + label + "." + field)
    for field in raw:
        if field not in FINDABLE_FIELDS:
            problems.append("unexpected field: " + label + "." + field)
    if problems:
        raise ValidationFailure(problems)
    if type(raw["id"]) is not int:
        raise ValidationFailure(["findable id not native integer: " + label])
    try:
        coins = require_native_amount(raw["coins"], label + ".coins")
    except ValidationFailure as failure:
        raise ValidationFailure(failure.problems)
    for field in ("title", "description"):
        if not isinstance(raw[field], str):
            raise ValidationFailure(["field not string: " + label + "." + field])
    return {
        "id": raw["id"],
        "title": raw["title"],
        "description": raw["description"],
        "coins": coins,
    }


def coerce_social(raw, label):
    """Coerce one stored social_items entry per rule S1 (verbatim)."""
    if not isinstance(raw, dict):
        raise ValidationFailure(["entry not object: " + label])
    problems = []
    for field in SOCIAL_FIELDS:
        if field not in raw:
            problems.append("missing field: " + label + "." + field)
    for field in raw:
        if field not in SOCIAL_FIELDS:
            problems.append("unexpected field: " + label + "." + field)
    if problems:
        raise ValidationFailure(problems)
    if type(raw["id"]) is not int:
        raise ValidationFailure(["social id not native integer: " + label])
    try:
        worker_cost = require_native_amount(raw["worker_cost"],
                                            label + ".worker_cost")
    except ValidationFailure as failure:
        raise ValidationFailure(failure.problems)
    for field in ("workers", "description"):
        if not isinstance(raw[field], str):
            raise ValidationFailure(["field not string: " + label + "." + field])
    if not raw["workers"]:
        raise ValidationFailure(["workers empty: " + label])
    return {
        "id": raw["id"],
        "workers": raw["workers"],
        "worker_cost": worker_cost,
        "description": raw["description"],
    }


def build_assist_definition(body, fingerprint):
    return {
        "legacy_id": str(body["position"]),
        "kind": "neighbor_assist",
        "source_file": MAIN_CONFIG_FILE.as_posix(),
        "source_layer": "stored",
        "content_version": fingerprint,
        "position": body["position"],
        "task": body["task"],
        "action": body["action"],
        "notification": body["notification"],
        "rnd": body["rnd"],
        "reward": dict(body["reward"]),
    }


def build_findable_definition(body, legacy_id, fingerprint):
    return {
        "legacy_id": legacy_id,
        "kind": "findable_item",
        "source_file": MAIN_CONFIG_FILE.as_posix(),
        "source_layer": "stored",
        "content_version": fingerprint,
        "id": body["id"],
        "title": body["title"],
        "description": body["description"],
        "coins": body["coins"],
    }


def build_social_definition(body, legacy_id, fingerprint):
    return {
        "legacy_id": legacy_id,
        "kind": "social_item",
        "source_file": MAIN_CONFIG_FILE.as_posix(),
        "source_layer": "stored",
        "content_version": fingerprint,
        "id": body["id"],
        "workers": body["workers"],
        "worker_cost": body["worker_cost"],
        "description": body["description"],
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


def check_round_trip(assists, findables, socials,
                     stored_assists, stored_findables, stored_socials):
    """Diff legacy re-emission against stored content exactly."""
    problems = []
    if len(assists) != len(stored_assists):
        problems.append("round-trip assist count mismatch: %d definitions vs %d stored"
                        % (len(assists), len(stored_assists)))
    else:
        for position, (definition, original) in enumerate(zip(assists, stored_assists)):
            entry_label = "round-trip assist " + definition["legacy_id"]
            if not isinstance(original, dict):
                problems.append(entry_label + ": stored entry not object")
                continue
            if definition["legacy_id"] != str(position):
                problems.append(entry_label + ": order/identity mismatch")
                continue
            try:
                body = coerce_assist(original, position, "round-trip")
            except ValidationFailure as failure:
                problems.extend([entry_label + ": " + item for item in failure.problems])
                continue
            for field in ("task", "action", "notification", "rnd"):
                if body[field] != definition[field]:
                    problems.append(entry_label + ": drift at " + field)
            if body["reward"] != definition["reward"]:
                problems.append(entry_label + ": drift at reward")
            if body["position"] != definition["position"]:
                problems.append(entry_label + ": drift at position")
            if set(original.keys()) != set(ASSIST_FIELDS):
                problems.append(entry_label + ": field-set drift "
                                + repr(sorted(set(original.keys()) ^ set(ASSIST_FIELDS))))
    if len(findables) != len(stored_findables):
        problems.append("round-trip findable count mismatch: %d definitions vs %d stored"
                        % (len(findables), len(stored_findables)))
    else:
        for definition, original in zip(findables, stored_findables):
            entry_label = "round-trip findable " + definition["legacy_id"]
            if not isinstance(original, dict):
                problems.append(entry_label + ": stored entry not object")
                continue
            if str(original.get("id")) != definition["legacy_id"]:
                problems.append(entry_label + ": order/identity mismatch")
                continue
            try:
                body = coerce_findable(original, "round-trip")
            except ValidationFailure as failure:
                problems.extend([entry_label + ": " + item for item in failure.problems])
                continue
            for field in ("id", "title", "description", "coins"):
                if body[field] != definition[field]:
                    problems.append(entry_label + ": drift at " + field)
            if set(original.keys()) != set(FINDABLE_FIELDS):
                problems.append(entry_label + ": field-set drift "
                                + repr(sorted(set(original.keys()) ^ set(FINDABLE_FIELDS))))
    if len(socials) != len(stored_socials):
        problems.append("round-trip social count mismatch: %d definitions vs %d stored"
                        % (len(socials), len(stored_socials)))
    else:
        for definition, original in zip(socials, stored_socials):
            entry_label = "round-trip social " + definition["legacy_id"]
            if not isinstance(original, dict):
                problems.append(entry_label + ": stored entry not object")
                continue
            if str(original.get("id")) != definition["legacy_id"]:
                problems.append(entry_label + ": order/identity mismatch")
                continue
            try:
                body = coerce_social(original, "round-trip")
            except ValidationFailure as failure:
                problems.extend([entry_label + ": " + item for item in failure.problems])
                continue
            for field in ("id", "workers", "worker_cost", "description"):
                if body[field] != definition[field]:
                    problems.append(entry_label + ": drift at " + field)
            if set(original.keys()) != set(SOCIAL_FIELDS):
                problems.append(entry_label + ": field-set drift "
                                + repr(sorted(set(original.keys()) ^ set(SOCIAL_FIELDS))))
    return problems


def load_all(root):
    """Load the stored social tables with patch-drift and mod guards."""
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
    for key in SOCIAL_KEYS:
        if key not in document or not isinstance(document[key], list):
            raise InputError("unsupported content shape: " + key + " not array")
        if len(document[key]) > MAX_TABLE_ENTRIES:
            raise InputError("table entry limit exceeded: " + key)
    patch_names = parse_patch_list(
        read_text_file(root / PATCH_LIST_FILE, "patch list"))
    mods_text = read_text_file(root / MODS_LIST_FILE, "mods list")
    active_mods, inactive_mods = parse_mods_list(mods_text)
    if active_mods:
        raise InputError("active mods unsupported, re-census required: "
                         + ", ".join(active_mods))
    check_no_social_patch_targets(root, patch_names)
    mods_bytes = read_bytes_file(root / MODS_LIST_FILE, "mods list")
    manifest_text = read_text_file(root / MANIFEST_FILE, "package manifest")
    try:
        manifest_document = json.loads(manifest_text)
    except ValueError:
        raise InputError("package manifest not valid json")
    if not isinstance(manifest_document, dict):
        raise InputError("package manifest not object")
    return {
        "neighbor_assists": document["neighbor_assists"],
        "findable_items": document["findable_items"],
        "social_items": document["social_items"],
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
    stored_assists = layers["neighbor_assists"]
    stored_findables = layers["findable_items"]
    stored_socials = layers["social_items"]
    problems = []
    assist_bodies = []
    for position, entry in enumerate(stored_assists):
        try:
            assist_bodies.append(coerce_assist(entry, position,
                                               "assist index " + str(position)))
        except ValidationFailure as failure:
            problems.extend(failure.problems)
    findable_bodies = []
    raw_findable_ids = []
    for entry in stored_findables:
        label = ("findable id " + repr(entry.get("id"))
                 if isinstance(entry, dict) else "findable entry")
        try:
            findable_bodies.append(coerce_findable(entry, label))
        except ValidationFailure as failure:
            problems.extend(failure.problems)
            continue
        raw_findable_ids.append(entry["id"] if isinstance(entry, dict) else entry)
    social_bodies = []
    raw_social_ids = []
    for entry in stored_socials:
        label = ("social id " + repr(entry.get("id"))
                 if isinstance(entry, dict) else "social entry")
        try:
            social_bodies.append(coerce_social(entry, label))
        except ValidationFailure as failure:
            problems.extend(failure.problems)
            continue
        raw_social_ids.append(entry["id"] if isinstance(entry, dict) else entry)
    if problems:
        raise ValidationFailure(problems)
    if len({str(entry_id) for entry_id in raw_findable_ids}) != len(raw_findable_ids):
        raise ValidationFailure(["duplicate findable legacy_id in stored findable_items"])
    if len({str(entry_id) for entry_id in raw_social_ids}) != len(raw_social_ids):
        raise ValidationFailure(["duplicate social legacy_id in stored social_items"])
    assists = [build_assist_definition(body, fingerprint)
               for body in assist_bodies]
    findables = [build_findable_definition(body, str(legacy_id), fingerprint)
                 for body, legacy_id in zip(findable_bodies, raw_findable_ids)]
    socials = [build_social_definition(body, str(legacy_id), fingerprint)
               for body, legacy_id in zip(social_bodies, raw_social_ids)]
    assist_schema = load_schema(root, ASSIST_SCHEMA_FILE.name, "neighbor_assist")
    findable_schema = load_schema(root, FINDABLE_SCHEMA_FILE.name, "findable_item")
    social_schema = load_schema(root, SOCIAL_SCHEMA_FILE.name, "social_item")
    for item in assists:
        problems.extend(validate_against_schema(
            item, assist_schema, "neighbor_assist " + item["legacy_id"]))
    for item in findables:
        problems.extend(validate_against_schema(
            item, findable_schema, "findable_item " + item["legacy_id"]))
    for item in socials:
        problems.extend(validate_against_schema(
            item, social_schema, "social_item " + item["legacy_id"]))
    if problems:
        raise ValidationFailure(problems)
    round_problems = check_round_trip(assists, findables, socials,
                                      stored_assists, stored_findables,
                                      stored_socials)
    if round_problems:
        raise ValidationFailure(round_problems)
    assist_rewards = {json.dumps(item["reward"], sort_keys=True) for item in assists}
    rnd_values = sorted({item["rnd"] for item in assists})
    findable_coins = sorted({item["coins"] for item in findables})
    description_empty = sum(1 for item in socials if not item["description"])
    worker_costs = sorted({item["worker_cost"] for item in socials})
    files = {
        ASSISTS_FILE: assists,
        FINDABLES_FILE: findables,
        SOCIAL_FILE: socials,
    }
    social_section = {
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
            "social_patch_targets": "none",
        },
        "coercion_ruleset": COERCION_RULESET_VERSION,
        "content_fingerprint": fingerprint,
        "counts": {
            "stored_assists": len(stored_assists),
            "stored_findables": len(stored_findables),
            "stored_socials": len(stored_socials),
            "assists": len(assists),
            "findables": len(findables),
            "socials": len(socials),
            "assist_reward_shapes": len(assist_rewards),
            "assist_rnd_values": rnd_values,
            "findable_coins_values": findable_coins,
            "social_description_empty": description_empty,
            "social_worker_costs": worker_costs,
        },
        "validation": {
            "duplicate_ids": 0,
            "amount_violations": 0,
            "missing_fields": 0,
            "round_trip_diffs": 0,
        },
        "outputs": [],
        "notes": [
            "Stored social tables map one-to-one to definitions; native "
            "amounts and display strings are kept verbatim with no string "
            "coercion and no embedded-JSON parsing (rule S1).",
            "Neighbor assists carry no stable stored id; legacy_id is the "
            "0-based positional index as a string and position preserves "
            "the entry order positionally (rule S2), matching the legacy "
            "positional loader.",
            "Findable and social legacy_id values are the decimal forms of "
            "the stored native integer ids (rule S2).",
            "Assist rewards are identical across all stored entries and "
            "findable coins are uniform; both are carried as stored, never "
            "factored out.",
            "Social description is empty in every stored entry; preserved "
            "verbatim with this note, never defaulted (rule S1).",
            "Reward amounts are coins/cash/xp literals and worker names "
            "are display data; neither is treated as an item reference.",
            "No active patch targets any social-table key; the build "
            "refuses patch drift and active mods explicitly.",
        ],
    }
    payloads = {}
    for path, entries in files.items():
        payloads[path] = json.dumps(entries, indent=2) + "\n"
    return social_section, payloads


def write_outputs(out_root, social_section, payloads):
    # Byte-exact writes: payloads are encoded once and the same bytes feed
    # the digest records. The social section is merged into the existing
    # package manifest (items, quests, tables, and economy keys preserved);
    # the manifest cannot digest itself, so only the three normalized files
    # are digested.
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
    social_section["outputs"] = outputs
    manifest_path = out / MANIFEST_FILE
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise InputError("package manifest not object")
    manifest["social"] = social_section
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
    social_section, payloads = build_package(repo_root, out_root)
    manifest = write_outputs(out_root, social_section, payloads)
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
        "counts": manifest["social"]["counts"],
        "outputs": [entry["file"] for entry in manifest["social"]["outputs"]],
        "problems": [],
    }
    print(json.dumps(report, indent=2, sort_keys=True) + "\n", end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
