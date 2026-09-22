"""Offline economy-schedules normalization builder and validator.

Loads the stored legacy economy schedules (`expansion_prices`, `town_prices`,
`map_prices`, and `level_ranking_reward` from `config/main.json`) directly
with no patch layering (no active patch targets any of the four keys;
verified per build), keeps every native number and object verbatim per the
documented economy coercion ruleset (citing the field-type survey),
validates positional uniqueness, non-negative amounts, ranking level
coverage 50..1, ranking unit references against the committed normalized
items legacy-ID set (the quest-precedent cross-domain edge), and
schema-required fields, and diffs a legacy-shaped re-emission against the
stored content exactly (round-trip fidelity gate). Schedule order is
positional and preserved; town and map schedules are preserved as separate
files even though their stored values are identical.

On success the normalized economy package (`normalized/expansion_prices.json`,
`normalized/town_prices.json`, `normalized/map_prices.json`,
`normalized/level_ranking_reward.json`, plus the `economy` section merged
into `manifest.json`) is written and exit 0 with a JSON report on stdout is
returned. Any validation failure exits 1 without writing output. Invalid
input or unsupported shapes exit 2. Standard library only: no legacy
application import, no runtime save reads, no network, server, browser, or
Flash activity.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys

COERCION_RULESET_VERSION = "economy-coercion-ruleset-v1"
POLICY = "economy-normalization-v1"

MAIN_CONFIG_FILE = Path("config") / "main.json"
PATCH_LIST_FILE = Path("config") / "patch" / "patches.txt"
PATCH_DIR = Path("config") / "patch"
MODS_LIST_FILE = Path("mods") / "mods.txt"
SCHEMA_DIR = Path("packages") / "game-content" / "schemas"
EXPANSION_SCHEMA_FILE = SCHEMA_DIR / "expansion_price.schema.json"
TOWN_SCHEMA_FILE = SCHEMA_DIR / "town_price.schema.json"
MAP_SCHEMA_FILE = SCHEMA_DIR / "map_price.schema.json"
RANKING_SCHEMA_FILE = SCHEMA_DIR / "level_ranking_reward.schema.json"
NORMALIZED_DIR = Path("packages") / "game-content" / "normalized"
BUILDINGS_FILE = NORMALIZED_DIR / "buildings.json"
UNITS_FILE = NORMALIZED_DIR / "units.json"
SPECIALS_FILE = NORMALIZED_DIR / "specials.json"
EXPANSION_FILE = NORMALIZED_DIR / "expansion_prices.json"
TOWN_FILE = NORMALIZED_DIR / "town_prices.json"
MAP_FILE = NORMALIZED_DIR / "map_prices.json"
RANKING_FILE = NORMALIZED_DIR / "level_ranking_reward.json"
MANIFEST_FILE = Path("packages") / "game-content" / "manifest.json"

MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_KEYS = 64
MAX_PATCH_FILES = 32
MAX_PATCH_OPS = 4096
MAX_SCHEDULE_ENTRIES = 4096

# Stored schedule field sets (field-type survey: expansion_prices native 4
# fields; town/map_prices native 3 fields; level_ranking_reward mixed with
# native level/cash plus a native units object). Anything else is drift.
EXPANSION_FIELDS = ("coins", "cash", "neighbors", "inventory_qte")
TOWN_FIELDS = ("coins", "cash", "level")
MAP_FIELDS = ("coins", "cash", "level")
RANKING_FIELDS = ("level", "cash", "units")

ECONOMY_KEYS = ("expansion_prices", "town_prices", "map_prices",
                "level_ranking_reward")


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


def check_no_economy_patch_targets(root, patch_names):
    """Refuse patch drift: no patch may target the four economy keys."""
    for name in patch_names:
        operations = load_patch_operations(root, name)
        for position, operation in enumerate(operations):
            if not isinstance(operation, dict):
                raise InputError("unsupported patch shape: " + name)
            target = operation.get("path")
            if not isinstance(target, str) or not target.startswith("/"):
                raise InputError("unsupported patch target path in " + name)
            key = target[1:].split("/", 1)[0] if len(target) > 1 else ""
            if key in ECONOMY_KEYS:
                raise InputError(
                    "patch targets economy-schedule content in " + name
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


def require_native_amount(value, label):
    """Rule E1: schedule amounts are native integers, never booleans."""
    if type(value) is not int:
        raise ValidationFailure(["field not native integer: " + label])
    if value < 0:
        raise ValidationFailure(["field negative: " + label])
    return value


def coerce_expansion(raw, position, label):
    """Coerce one stored expansion_prices entry per rule E1 (verbatim native)."""
    if not isinstance(raw, dict):
        raise ValidationFailure(["entry not object: " + label])
    problems = []
    for field in EXPANSION_FIELDS:
        if field not in raw:
            problems.append("missing field: " + label + "." + field)
    for field in raw:
        if field not in EXPANSION_FIELDS:
            problems.append("unexpected field: " + label + "." + field)
    if problems:
        raise ValidationFailure(problems)
    body = {"position": position}
    for field in EXPANSION_FIELDS:
        try:
            body[field] = require_native_amount(raw[field], label + "." + field)
        except ValidationFailure as failure:
            raise ValidationFailure(failure.problems)
    return body


def coerce_town(raw, position, label):
    """Coerce one stored town_prices entry per rule E1 (verbatim native)."""
    if not isinstance(raw, dict):
        raise ValidationFailure(["entry not object: " + label])
    problems = []
    for field in TOWN_FIELDS:
        if field not in raw:
            problems.append("missing field: " + label + "." + field)
    for field in raw:
        if field not in TOWN_FIELDS:
            problems.append("unexpected field: " + label + "." + field)
    if problems:
        raise ValidationFailure(problems)
    body = {"position": position}
    for field in TOWN_FIELDS:
        try:
            body[field] = require_native_amount(raw[field], label + "." + field)
        except ValidationFailure as failure:
            raise ValidationFailure(failure.problems)
    return body


def coerce_map(raw, position, label):
    """Coerce one stored map_prices entry per rule E1 (verbatim native)."""
    if not isinstance(raw, dict):
        raise ValidationFailure(["entry not object: " + label])
    problems = []
    for field in MAP_FIELDS:
        if field not in raw:
            problems.append("missing field: " + label + "." + field)
    for field in raw:
        if field not in MAP_FIELDS:
            problems.append("unexpected field: " + label + "." + field)
    if problems:
        raise ValidationFailure(problems)
    body = {"position": position}
    for field in MAP_FIELDS:
        try:
            body[field] = require_native_amount(raw[field], label + "." + field)
        except ValidationFailure as failure:
            raise ValidationFailure(failure.problems)
    return body


def coerce_ranking(raw, label):
    """Coerce one stored level_ranking_reward entry per rules E1/E3."""
    if not isinstance(raw, dict):
        raise ValidationFailure(["entry not object: " + label])
    problems = []
    for field in RANKING_FIELDS:
        if field not in raw:
            problems.append("missing field: " + label + "." + field)
    for field in raw:
        if field not in RANKING_FIELDS:
            problems.append("unexpected field: " + label + "." + field)
    if problems:
        raise ValidationFailure(problems)
    if type(raw["level"]) is not int:
        raise ValidationFailure(["ranking level not native integer: " + label])
    if raw["level"] < 1:
        raise ValidationFailure(["ranking level below 1: " + label])
    if type(raw["cash"]) is not int:
        raise ValidationFailure(["ranking cash not native integer: " + label])
    if raw["cash"] < 0:
        raise ValidationFailure(["ranking cash negative: " + label])
    units = raw["units"]
    if not isinstance(units, dict) or not units:
        raise ValidationFailure(["ranking units not non-empty object: " + label])
    quantities = {}
    for key, value in units.items():
        if not isinstance(key, str) or not key:
            raise ValidationFailure(["ranking units key not string: " + label])
        if type(value) is not int:
            raise ValidationFailure(["ranking units quantity not native integer: "
                                     + label + "." + key])
        if value < 1:
            raise ValidationFailure(["ranking units quantity not positive: "
                                     + label + "." + key])
        quantities[key] = value
    return {
        "level": raw["level"],
        "cash": raw["cash"],
        "units": quantities,
        "unit_refs": sorted(quantities.keys()),
    }


def build_expansion_definition(body, fingerprint):
    return {
        "legacy_id": str(body["position"]),
        "kind": "expansion_price",
        "source_file": MAIN_CONFIG_FILE.as_posix(),
        "source_layer": "stored",
        "content_version": fingerprint,
        "position": body["position"],
        "coins": body["coins"],
        "cash": body["cash"],
        "neighbors": body["neighbors"],
        "inventory_qte": body["inventory_qte"],
    }


def build_town_definition(body, fingerprint):
    return {
        "legacy_id": str(body["position"]),
        "kind": "town_price",
        "source_file": MAIN_CONFIG_FILE.as_posix(),
        "source_layer": "stored",
        "content_version": fingerprint,
        "position": body["position"],
        "coins": body["coins"],
        "cash": body["cash"],
        "level": body["level"],
    }


def build_map_definition(body, fingerprint):
    return {
        "legacy_id": str(body["position"]),
        "kind": "map_price",
        "source_file": MAIN_CONFIG_FILE.as_posix(),
        "source_layer": "stored",
        "content_version": fingerprint,
        "position": body["position"],
        "coins": body["coins"],
        "cash": body["cash"],
        "level": body["level"],
    }


def build_ranking_definition(body, fingerprint):
    return {
        "legacy_id": str(body["level"]),
        "kind": "level_ranking_reward",
        "source_file": MAIN_CONFIG_FILE.as_posix(),
        "source_layer": "stored",
        "content_version": fingerprint,
        "level": body["level"],
        "cash": body["cash"],
        "units": dict(body["units"]),
        "unit_refs": list(body["unit_refs"]),
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


def validate_ranking_references(rankings, items_id_set):
    """Rule E3: every ranking units key must resolve to a normalized item."""
    problems = []
    for definition in rankings:
        for key in definition["unit_refs"]:
            if key not in items_id_set:
                problems.append("unresolvable ranking unit reference: "
                                + definition["legacy_id"] + " -> " + key)
        if definition["unit_refs"] != sorted(definition["units"].keys()):
            problems.append("unit_refs drift at ranking "
                            + definition["legacy_id"])
    return problems


def check_round_trip(expansion, town, maps, ranking,
                     stored_expansion, stored_town, stored_maps,
                     stored_ranking):
    """Diff legacy re-emission against stored content exactly."""
    problems = []
    pairs = (
        ("expansion price", expansion, stored_expansion, EXPANSION_FIELDS),
        ("town price", town, stored_town, TOWN_FIELDS),
        ("map price", maps, stored_maps, MAP_FIELDS),
    )
    for label, definitions, stored, fields in pairs:
        if len(definitions) != len(stored):
            problems.append("round-trip " + label + " count mismatch: %d definitions vs %d stored"
                            % (len(definitions), len(stored)))
            continue
        for position, (definition, original) in enumerate(zip(definitions, stored)):
            entry_label = "round-trip " + label + " " + definition["legacy_id"]
            if not isinstance(original, dict):
                problems.append(entry_label + ": stored entry not object")
                continue
            if definition["legacy_id"] != str(position):
                problems.append(entry_label + ": order/identity mismatch")
                continue
            try:
                if label == "expansion price":
                    body = coerce_expansion(original, position, "round-trip")
                elif label == "town price":
                    body = coerce_town(original, position, "round-trip")
                else:
                    body = coerce_map(original, position, "round-trip")
            except ValidationFailure as failure:
                problems.extend([entry_label + ": " + item for item in failure.problems])
                continue
            for field in fields:
                if body[field] != definition[field]:
                    problems.append(entry_label + ": drift at " + field)
            if body["position"] != definition["position"]:
                problems.append(entry_label + ": drift at position")
            if set(original.keys()) != set(fields):
                problems.append(entry_label + ": field-set drift "
                                + repr(sorted(set(original.keys()) ^ set(fields))))
    if len(ranking) != len(stored_ranking):
        problems.append("round-trip ranking reward count mismatch: %d definitions vs %d stored"
                        % (len(ranking), len(stored_ranking)))
    else:
        for definition, original in zip(ranking, stored_ranking):
            entry_label = "round-trip ranking reward " + definition["legacy_id"]
            if not isinstance(original, dict):
                problems.append(entry_label + ": stored entry not object")
                continue
            if str(original.get("level")) != definition["legacy_id"]:
                problems.append(entry_label + ": order/identity mismatch")
                continue
            try:
                body = coerce_ranking(original, "round-trip")
            except ValidationFailure as failure:
                problems.extend([entry_label + ": " + item for item in failure.problems])
                continue
            for field in ("level", "cash"):
                if body[field] != definition[field]:
                    problems.append(entry_label + ": drift at " + field)
            if body["units"] != definition["units"]:
                problems.append(entry_label + ": drift at units")
            if body["unit_refs"] != definition["unit_refs"]:
                problems.append(entry_label + ": drift at unit_refs")
            if set(original.keys()) != set(RANKING_FIELDS):
                problems.append(entry_label + ": field-set drift "
                                + repr(sorted(set(original.keys()) ^ set(RANKING_FIELDS))))
    return problems


def load_all(root):
    """Load the stored economy schedules with patch-drift and mod guards."""
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
    for key in ECONOMY_KEYS:
        if key not in document or not isinstance(document[key], list):
            raise InputError("unsupported content shape: " + key + " not array")
        if len(document[key]) > MAX_SCHEDULE_ENTRIES:
            raise InputError("schedule entry limit exceeded: " + key)
    patch_names = parse_patch_list(
        read_text_file(root / PATCH_LIST_FILE, "patch list"))
    mods_text = read_text_file(root / MODS_LIST_FILE, "mods list")
    active_mods, inactive_mods = parse_mods_list(mods_text)
    if active_mods:
        raise InputError("active mods unsupported, re-census required: "
                         + ", ".join(active_mods))
    check_no_economy_patch_targets(root, patch_names)
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
        "expansion_prices": document["expansion_prices"],
        "town_prices": document["town_prices"],
        "map_prices": document["map_prices"],
        "level_ranking_reward": document["level_ranking_reward"],
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
    stored_expansion = layers["expansion_prices"]
    stored_town = layers["town_prices"]
    stored_maps = layers["map_prices"]
    stored_ranking = layers["level_ranking_reward"]
    problems = []
    expansion_bodies = []
    for position, entry in enumerate(stored_expansion):
        try:
            expansion_bodies.append(coerce_expansion(entry, position,
                                                     "expansion price index "
                                                     + str(position)))
        except ValidationFailure as failure:
            problems.extend(failure.problems)
    town_bodies = []
    for position, entry in enumerate(stored_town):
        try:
            town_bodies.append(coerce_town(entry, position,
                                           "town price index " + str(position)))
        except ValidationFailure as failure:
            problems.extend(failure.problems)
    map_bodies = []
    for position, entry in enumerate(stored_maps):
        try:
            map_bodies.append(coerce_map(entry, position,
                                         "map price index " + str(position)))
        except ValidationFailure as failure:
            problems.extend(failure.problems)
    ranking_bodies = []
    for entry in stored_ranking:
        label = ("ranking reward level " + repr(entry.get("level"))
                 if isinstance(entry, dict) else "ranking reward entry")
        try:
            ranking_bodies.append(coerce_ranking(entry, label))
        except ValidationFailure as failure:
            problems.extend(failure.problems)
    if problems:
        raise ValidationFailure(problems)
    expansion = [build_expansion_definition(body, fingerprint)
                 for body in expansion_bodies]
    town = [build_town_definition(body, fingerprint)
            for body in town_bodies]
    maps = [build_map_definition(body, fingerprint)
            for body in map_bodies]
    ranking = [build_ranking_definition(body, fingerprint)
               for body in ranking_bodies]
    if len({item["legacy_id"] for item in expansion}) != len(expansion):
        raise ValidationFailure(["duplicate expansion_price legacy_id"])
    if len({item["legacy_id"] for item in town}) != len(town):
        raise ValidationFailure(["duplicate town_price legacy_id"])
    if len({item["legacy_id"] for item in maps}) != len(maps):
        raise ValidationFailure(["duplicate map_price legacy_id"])
    ranking_levels = [item["level"] for item in ranking]
    if len(set(ranking_levels)) != len(ranking_levels):
        raise ValidationFailure(["duplicate ranking level in stored level_ranking_reward"])
    if set(ranking_levels) != set(range(1, 51)):
        raise ValidationFailure(["ranking level coverage not exactly 50..1: "
                                 + repr(sorted(ranking_levels))])
    problems.extend(validate_ranking_references(ranking, layers["items_id_set"]))
    if problems:
        raise ValidationFailure(problems)
    expansion_schema = load_schema(root, EXPANSION_SCHEMA_FILE.name, "expansion_price")
    town_schema = load_schema(root, TOWN_SCHEMA_FILE.name, "town_price")
    map_schema = load_schema(root, MAP_SCHEMA_FILE.name, "map_price")
    ranking_schema = load_schema(root, RANKING_SCHEMA_FILE.name, "level_ranking_reward")
    for item in expansion:
        problems.extend(validate_against_schema(
            item, expansion_schema, "expansion_price " + item["legacy_id"]))
    for item in town:
        problems.extend(validate_against_schema(
            item, town_schema, "town_price " + item["legacy_id"]))
    for item in maps:
        problems.extend(validate_against_schema(
            item, map_schema, "map_price " + item["legacy_id"]))
    for item in ranking:
        problems.extend(validate_against_schema(
            item, ranking_schema, "level_ranking_reward " + item["legacy_id"]))
    if problems:
        raise ValidationFailure(problems)
    round_problems = check_round_trip(expansion, town, maps, ranking,
                                      stored_expansion, stored_town,
                                      stored_maps, stored_ranking)
    if round_problems:
        raise ValidationFailure(round_problems)
    town_map_identical = (
        len(stored_town) == len(stored_maps)
        and all(first == second
                for first, second in zip(stored_town, stored_maps)))
    cash_values = sorted({item["cash"] for item in ranking})
    files = {
        EXPANSION_FILE: expansion,
        TOWN_FILE: town,
        MAP_FILE: maps,
        RANKING_FILE: ranking,
    }
    economy_section = {
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
            "economy_patch_targets": "none",
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
            "stored_expansion_prices": len(stored_expansion),
            "stored_town_prices": len(stored_town),
            "stored_map_prices": len(stored_maps),
            "stored_ranking_rewards": len(stored_ranking),
            "expansion_prices": len(expansion),
            "town_prices": len(town),
            "map_prices": len(maps),
            "ranking_rewards": len(ranking),
            "ranking_level_min": min(ranking_levels),
            "ranking_level_max": max(ranking_levels),
            "ranking_cash_values": cash_values,
            "town_map_values_identical": town_map_identical,
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
            "Stored price schedules map one-to-one to definitions; every "
            "native amount is kept verbatim with no string coercion and no "
            "embedded-JSON parsing (rule E1).",
            "Price schedules carry no stable stored id; legacy_id is the "
            "0-based positional index as a string and position preserves "
            "the schedule order positionally (rule E2), matching the "
            "legacy positional loader.",
            "Town and map stored values are identical as observed but are "
            "preserved as separate schedules, never merged or deduplicated.",
            "Ranking legacy_id is the decimal form of the stored native "
            "integer level; rows cover 50..1 exactly once (rule E2).",
            "Ranking units keys resolve against the normalized items "
            "legacy-ID set with unit_refs carried in sorted order; "
            "unresolvable references fail validation (rule E3).",
            "No active patch targets any economy-schedule key; the build "
            "refuses patch drift and active mods explicitly.",
        ],
    }
    payloads = {}
    for path, entries in files.items():
        payloads[path] = json.dumps(entries, indent=2) + "\n"
    return economy_section, payloads


def write_outputs(out_root, economy_section, payloads):
    # Byte-exact writes: payloads are encoded once and the same bytes feed
    # the digest records. The economy section is merged into the existing
    # package manifest (items, quests, and tables keys preserved); the
    # manifest cannot digest itself, so only the four normalized files are
    # digested.
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
    economy_section["outputs"] = outputs
    manifest_path = out / MANIFEST_FILE
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise InputError("package manifest not object")
    manifest["economy"] = economy_section
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
    economy_section, payloads = build_package(repo_root, out_root)
    manifest = write_outputs(out_root, economy_section, payloads)
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
        "counts": manifest["economy"]["counts"],
        "outputs": [entry["file"] for entry in manifest["economy"]["outputs"]],
        "problems": [],
    }
    print(json.dumps(report, indent=2, sort_keys=True) + "\n", end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
