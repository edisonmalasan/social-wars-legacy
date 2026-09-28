"""Offline validator for the committed normalized content package.

Reads exactly the committed package - ``packages/game-content/manifest.json``,
the normalized outputs the manifest records, and the schema files - and checks
four families: package structure and hygiene, manifest integrity, schema
conformance, and dependency/reference integrity.  Standard library only; never
imports the builders or any legacy module; writes nothing; no wall clock, no
network, no legacy sources.

Schema subset (the same subset the builders document and enforce): required,
type unions (integer, number, string, boolean, object, array, null; a boolean
is never an integer or a number), const, enum (strings only), property-level
minimum (native integers), minItems, minProperties, array element types,
propertyNames, additionalProperties (false at the top level, or a nested
{type, minimum} gate over object values).

Exit codes: 0 - valid, JSON success report on stdout; 1 - validation-failed
report listing each problem on stdout, nothing written; 2 - invalid input or
unsupported shape (missing/unreadable/unparseable file, invalid schema, bad
usage) on stderr, no validity claim.
"""

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

PACKAGE_REL = ("packages", "game-content")
SECTION_NAMES = (
    "quests", "tables", "economy", "social", "taxonomy",
    "darts", "globals", "offers", "images",
)

# Output file -> (section or None for the root record, count key that names
# that file's entries, schema file or None for the schema-less special).
FILE_MAP = {
    "buildings.json": (None, "buildings", "building.schema.json"),
    "units.json": (None, "units", "unit.schema.json"),
    "specials.json": (None, "specials", None),
    "quests.json": ("quests", "quests", "quest.schema.json"),
    "collections.json": ("quests", "collections", "collection.schema.json"),
    "levels.json": ("tables", "levels", "level.schema.json"),
    "magics.json": ("tables", "magics", "magic.schema.json"),
    "sounds.json": ("tables", "sounds", "sound.schema.json"),
    "expansion_prices.json": (
        "economy", "expansion_prices", "expansion_price.schema.json"),
    "town_prices.json": ("economy", "town_prices", "town_price.schema.json"),
    "map_prices.json": ("economy", "map_prices", "map_price.schema.json"),
    "level_ranking_reward.json": (
        "economy", "ranking_rewards", "level_ranking_reward.schema.json"),
    "neighbor_assists.json": (
        "social", "assists", "neighbor_assist.schema.json"),
    "findable_items.json": (
        "social", "findables", "findable_item.schema.json"),
    "social_items.json": ("social", "socials", "social_item.schema.json"),
    "categories.json": ("taxonomy", "categories", "category.schema.json"),
    "inventory_items.json": (
        "taxonomy", "inventory", "inventory_item.schema.json"),
    "unit_collection_categories.json": (
        "taxonomy", "collections", "unit_collection_category.schema.json"),
    "darts_items.json": ("darts", "darts", "darts_item.schema.json"),
    "globals.json": ("globals", "globals", "global_entry.schema.json"),
    "offer_packs.json": ("offers", "offers", "offer_pack.schema.json"),
    "images.json": ("images", "images", "image_asset.schema.json"),
}

ITEM_FILES = ("buildings.json", "units.json", "specials.json")
INVENTORY_FILE = "inventory_items.json"

RELATION_NONE = (-1, 0)
SPECIAL_ID = "925"
SPECIAL_KIND = "special"
SPECIAL_NOTE = (
    "Stored type l (land) entry: Expandable Land is terrain inventory, not "
    "a building or unit. It is normalized as a documented special with the "
    "same coercion rules; its empty properties string marks absence of a "
    "property map (rule R3) and its empty group_type is preserved (rule R3)."
)

# Rule F3 pinned offer anomalies, asserted exactly as documented.
ANOMALY_OFFER_ID = 4
ANOMALY_PAIR_SECOND = 35
ANOMALY_FLOAT_OFFER_ID = 35
ANOMALY_FLOAT_VALUE = 1072.1224

USAGE = "usage: validate_content.py [--repo-root PATH]"

FAMILY_STRUCTURE = "structure"
FAMILY_MANIFEST = "manifest"
FAMILY_SCHEMA = "schema"
FAMILY_SPECIAL = "special"
FAMILY_DEPENDENCY = "dependency"


class InvalidInput(Exception):
    """Invalid input or unsupported shape: exit 2 with no validity claim."""


def is_native_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def problem(family, file, entry="", field="", message=""):
    return {
        "family": family,
        "file": file,
        "entry": str(entry),
        "field": field,
        "message": message,
    }


def problem_sort_key(item):
    return (item["family"], item["file"], item["entry"],
            item["field"], item["message"])


def parse_args(argv):
    repo_root = "."
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--repo-root":
            index += 1
            if index >= len(argv):
                raise InvalidInput(USAGE + " (missing PATH after --repo-root)")
            repo_root = argv[index]
        elif arg in ("-h", "--help"):
            return None
        else:
            raise InvalidInput(USAGE + " (unknown argument: " + arg + ")")
        index += 1
    return repo_root


def load_json_bytes(raw, label):
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise InvalidInput(label + " is not valid utf-8")
    try:
        return json.loads(text)
    except ValueError as error:
        raise InvalidInput(label + " is not valid json: " + str(error))


def load_json_file(path, label):
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise InvalidInput("cannot read " + label + ": " + str(error))
    return load_json_bytes(raw, label)


def load_schema(path, label):
    """Structural rules for a schema file itself; invalid input = exit 2."""
    schema = load_json_file(path, label)
    if not isinstance(schema, dict):
        raise InvalidInput(label + " is not a json object")
    if schema.get("type") != "object":
        raise InvalidInput(label + " is not an object schema")
    required = schema.get("required")
    properties = schema.get("properties")
    if not isinstance(required, list):
        raise InvalidInput(label + " required is not a list")
    if not isinstance(properties, dict):
        raise InvalidInput(label + " properties is not an object")
    for field in required:
        if field not in properties:
            raise InvalidInput(label + " required field not in properties: "
                               + str(field))
    kind = properties.get("kind")
    const = kind.get("const") if isinstance(kind, dict) else None
    if not isinstance(const, str) or not const:
        raise InvalidInput(label + " kind const missing")
    return schema


def check_schema_type(value, allowed, field, problems):
    """One JSON-Schema type union; bool never counts as integer or number."""
    for kind in allowed:
        if kind == "integer" and type(value) is int:
            return
        if kind == "number" and isinstance(value, (int, float)) \
                and not isinstance(value, bool):
            return
        if kind == "string" and isinstance(value, str):
            return
        if kind == "boolean" and type(value) is bool:
            return
        if kind == "object" and isinstance(value, dict):
            return
        if kind == "array" and isinstance(value, list):
            return
        if kind == "null" and value is None:
            return
    problems.append((field, "type mismatch: expected "
                     + "/".join(allowed)))


def check_entry(entry, schema):
    """Enforce the documented schema subset; returns [(field, message)]."""
    problems = []
    if not isinstance(entry, dict):
        return [("", "entry is not an object")]
    for field in schema["required"]:
        if field not in entry:
            problems.append((field, "missing required field"))
    for field, spec in schema["properties"].items():
        if field not in entry:
            continue
        if not isinstance(spec, dict):
            continue
        value = entry[field]
        if "const" in spec:
            if value != spec["const"]:
                problems.append((field, "const mismatch"))
            continue
        allowed = spec.get("type")
        if isinstance(allowed, str):
            allowed = [allowed]
        if allowed:
            check_schema_type(value, allowed, field, problems)
        if "enum" in spec and isinstance(value, str):
            if value not in spec["enum"]:
                problems.append((field, "enum mismatch"))
        if "minimum" in spec and type(value) is int:
            if value < spec["minimum"]:
                problems.append((field, "value below minimum"))
        if "minItems" in spec and isinstance(value, list):
            if len(value) < spec["minItems"]:
                problems.append((field, "array below minItems"))
        items_spec = spec.get("items")
        if isinstance(value, list) and isinstance(items_spec, dict):
            item_types = items_spec.get("type")
            if isinstance(item_types, str):
                item_types = [item_types]
            if item_types:
                for index, element in enumerate(value):
                    sub = []
                    check_schema_type(
                        element, item_types, "%s[%d]" % (field, index), sub)
                    problems.extend(sub)
        if "minProperties" in spec and isinstance(value, dict):
            if len(value) < spec["minProperties"]:
                problems.append((field, "object below minProperties"))
        names = spec.get("propertyNames")
        if isinstance(value, dict) and isinstance(names, dict):
            allowed_names = names.get("enum", [])
            for key in value:
                if key not in allowed_names:
                    problems.append(
                        (field, "property name outside set: " + repr(key)))
        additional = spec.get("additionalProperties")
        if isinstance(value, dict) and isinstance(additional, dict):
            for key, amount in value.items():
                sub_field = field + "." + str(key)
                if "type" in additional:
                    sub = []
                    check_schema_type(
                        amount, [additional["type"]], sub_field, sub)
                    problems.extend(sub)
                if "minimum" in additional \
                        and isinstance(amount, (int, float)) \
                        and not isinstance(amount, bool):
                    if amount < additional["minimum"]:
                        problems.append(
                            (sub_field, "value below minimum"))
    if schema.get("additionalProperties") is False:
        for field in entry:
            if field not in schema["properties"]:
                problems.append((field, "additional property not in schema"))
    return problems


def check_special(entries):
    """Documented gates for the schema-less special file."""
    problems = []
    if len(entries) != 1:
        problems.append(
            ("", "expected exactly one special entry, found %d"
             % len(entries)))
        return problems
    entry = entries[0]
    if not isinstance(entry, dict):
        return [("", "entry is not an object")]
    if entry.get("legacy_id") != SPECIAL_ID:
        problems.append(
            ("legacy_id", "special legacy_id must be %r, found %r"
             % (SPECIAL_ID, entry.get("legacy_id"))))
    if entry.get("kind") != SPECIAL_KIND:
        problems.append(
            ("kind", "special kind must be %r, found %r"
             % (SPECIAL_KIND, entry.get("kind"))))
    if entry.get("special_note") != SPECIAL_NOTE:
        problems.append(("special_note", "special_note differs from the "
                         "documented note"))
    return problems


def derive_offer_refs(entry, items_ids, label):
    """Rule F3: derive refs and flag unresolving leaves (anomalies pinned)."""
    refs = []
    problems = []
    shape = entry.get("items_shape")
    body = entry.get("items")
    if shape == "null":
        return refs, problems
    if not isinstance(body, list):
        return refs, [("items", "offer items is not an array")]
    if shape == "flat":
        for value in body:
            if str(value) not in items_ids:
                problems.append(
                    ("item_refs", "unresolvable offer leaf: "
                     + label + " -> " + repr(value)))
            else:
                refs.append(str(value))
        return refs, problems
    offer_id = entry.get("id")
    for group in body:
        if shape == "pairs":
            if not isinstance(group, list) or len(group) != 2:
                problems.append(
                    ("items", "malformed offer pair group: " + label))
                continue
            first, second = group
            if not is_native_int(first):
                problems.append(
                    ("items", "pair first not native integer: " + label))
                continue
            if str(first) not in items_ids:
                problems.append(
                    ("item_refs", "unresolvable offer pair reference: "
                     + label + " -> " + repr(first)))
            else:
                refs.append(str(first))
            if isinstance(second, bool) or not isinstance(second, (int, float)):
                problems.append(
                    ("items", "pair second not number: " + label))
            continue
        if not isinstance(group, list):
            problems.append(("items", "group leaf container is not an "
                             "array: " + label))
            continue
        for value in group:
            if isinstance(value, bool):
                problems.append(
                    ("items", "group leaf is boolean: " + label))
            elif is_native_int(value):
                if str(value) not in items_ids:
                    problems.append(
                        ("item_refs", "unresolvable offer group reference: "
                         + label + " -> " + repr(value)))
                else:
                    refs.append(str(value))
            elif isinstance(value, float):
                if offer_id == ANOMALY_FLOAT_OFFER_ID \
                        and value == ANOMALY_FLOAT_VALUE:
                    continue
                problems.append(
                    ("items", "non-integer group leaf: "
                     + label + " -> " + repr(value)))
            else:
                problems.append(
                    ("items", "unexpected group leaf type: "
                     + label + " -> " + repr(value)))
    return refs, problems


def check_offer_anomalies(entry):
    problems = []
    body = entry.get("items")
    offer_id = entry.get("id")
    if offer_id == ANOMALY_OFFER_ID:
        present = isinstance(body, list) and any(
            isinstance(group, list) and len(group) >= 2
            and group[1] == ANOMALY_PAIR_SECOND
            for group in body)
        if not present:
            problems.append(
                ("items", "pinned anomaly (%d, %d) not present as "
                 "documented" % (ANOMALY_OFFER_ID, ANOMALY_PAIR_SECOND)))
    if offer_id == ANOMALY_FLOAT_OFFER_ID:
        present = isinstance(body, list) and any(
            value == ANOMALY_FLOAT_VALUE
            for group in body if isinstance(group, list)
            for value in group)
        if not present:
            problems.append(
                ("items", "pinned anomaly (%d, %r) not present as "
                 "documented" % (ANOMALY_FLOAT_OFFER_ID,
                                 ANOMALY_FLOAT_VALUE)))
    return problems


def read_outputs(repo_root, manifest, problems):
    """Read every recorded output; unreadable input raises InvalidInput."""
    records = []
    root_outputs = manifest.get("outputs")
    if not isinstance(root_outputs, list):
        raise InvalidInput("manifest root outputs missing or not a list")
    records.append((None, manifest, root_outputs))
    for section in SECTION_NAMES:
        record = manifest.get(section)
        if isinstance(record, dict):
            outputs = record.get("outputs")
            if not isinstance(outputs, list):
                problems.append(problem(
                    FAMILY_STRUCTURE, "manifest.json", "",
                    section + ".outputs",
                    "extension section outputs missing or not a list"))
                outputs = []
            records.append((section, record, outputs))
        else:
            problems.append(problem(
                FAMILY_STRUCTURE, "manifest.json", "", section,
                "extension section record missing"))

    recorded = {}
    for section, record, outputs in records:
        for output in outputs:
            if not isinstance(output, dict) \
                    or not isinstance(output.get("file"), str):
                raise InvalidInput("unsupported manifest output record")
            file_path = output["file"]
            name = file_path.replace("\\", "/").rsplit("/", 1)[-1]
            if name in recorded:
                raise InvalidInput("duplicate recorded output: " + name)
            recorded[name] = (file_path, output, section, record)

    for name in sorted(recorded):
        if name not in FILE_MAP:
            problems.append(problem(
                FAMILY_STRUCTURE, name, "", "",
                "recorded output has no validator mapping"))
    for name in sorted(FILE_MAP):
        if name not in recorded:
            problems.append(problem(
                FAMILY_STRUCTURE, name, "", "",
                "expected output not recorded in manifest"))

    loaded = {}
    for name in sorted(recorded):
        file_path, output, section, record = recorded[name]
        normalized = "/".join(PACKAGE_REL) + "/normalized/"
        if not file_path.replace("\\", "/").startswith(normalized):
            raise InvalidInput(
                "recorded output outside the package: " + file_path)
        if name not in FILE_MAP:
            continue
        path = repo_root.joinpath(*PACKAGE_REL, "normalized", name)
        if not path.is_file():
            raise InvalidInput("missing recorded output: " + name)
        try:
            raw = path.read_bytes()
        except OSError as error:
            raise InvalidInput("cannot read " + name + ": " + str(error))
        entries = load_json_bytes(raw, name)
        if not isinstance(entries, list):
            raise InvalidInput(name + " is not an array of entries")
        loaded[name] = {
            "raw": raw,
            "entries": entries,
            "record": output,
            "section": section,
            "section_record": record,
        }
        expected_bytes = output.get("bytes")
        expected_sha = output.get("sha256")
        if not isinstance(expected_bytes, int) \
                or not isinstance(expected_sha, str):
            raise InvalidInput("unsupported digest record for " + name)
        if len(raw) != expected_bytes:
            problems.append(problem(
                FAMILY_MANIFEST, name, "", "bytes",
                "recorded %d bytes, actual %d"
                % (expected_bytes, len(raw))))
        actual_sha = hashlib.sha256(raw).hexdigest()
        if actual_sha != expected_sha:
            problems.append(problem(
                FAMILY_MANIFEST, name, "", "sha256",
                "recorded %s, actual %s" % (expected_sha, actual_sha)))
    return loaded, recorded


def check_directory_hygiene(repo_root, recorded, problems):
    normalized = repo_root.joinpath(*PACKAGE_REL, "normalized")
    if not normalized.is_dir():
        raise InvalidInput("normalized directory missing")
    actual = {entry.name for entry in normalized.iterdir()
              if entry.is_file()}
    for name in sorted(actual - set(recorded)):
        problems.append(problem(
            FAMILY_STRUCTURE, name, "", "",
            "unrecorded file in normalized directory"))


def check_record_fields(manifest, problems):
    records = [(None, manifest)] + [
        (section, manifest.get(section)) for section in SECTION_NAMES]
    for section, record in records:
        label = "manifest.json" if section is None else section
        if not isinstance(record, dict):
            continue
        if "schema_version" not in record:
            problems.append(problem(
                FAMILY_STRUCTURE, "manifest.json", "",
                label + ".schema_version", "schema_version missing"))
        if record.get("result") != "success":
            problems.append(problem(
                FAMILY_STRUCTURE, "manifest.json", "",
                label + ".result",
                "recorded result is %r, expected 'success'"
                % (record.get("result"),)))
        policy = record.get("policy")
        if not isinstance(policy, str) or not policy:
            problems.append(problem(
                FAMILY_STRUCTURE, "manifest.json", "",
                label + ".policy", "policy missing or not a string"))


def check_counts(loaded, problems):
    for name in sorted(FILE_MAP):
        if name not in loaded:
            continue
        section, count_key, _schema = FILE_MAP[name]
        label = section if section is not None else "root"
        counts = loaded[name]["section_record"].get("counts")
        if not isinstance(counts, dict):
            problems.append(problem(
                FAMILY_MANIFEST, name, "", "counts",
                "section %s: counts missing or not an object" % label))
            continue
        if count_key not in counts:
            problems.append(problem(
                FAMILY_MANIFEST, name, "", count_key,
                "section %s: count key missing from counts" % label))
            continue
        recorded = counts[count_key]
        actual = len(loaded[name]["entries"])
        if recorded != actual:
            problems.append(problem(
                FAMILY_MANIFEST, name, "", count_key,
                "section %s: recorded %r, actual %d entries"
                % (label, recorded, actual)))


def check_schemas(repo_root, problems):
    schemas = {}
    for name in sorted(FILE_MAP):
        schema_name = FILE_MAP[name][2]
        if schema_name is None:
            continue
        path = repo_root.joinpath(*PACKAGE_REL, "schemas", schema_name)
        if not path.is_file():
            raise InvalidInput("missing schema file: " + schema_name)
        schemas[name] = load_schema(path, schema_name)
    return schemas


def check_entries(loaded, schemas, problems):
    for name in sorted(FILE_MAP):
        if name not in loaded:
            continue
        entries = loaded[name]["entries"]
        if name == "specials.json":
            for field, message in check_special(entries):
                problems.append(problem(
                    FAMILY_SPECIAL, name, SPECIAL_ID, field, message))
            continue
        schema = schemas[name]
        for index, entry in enumerate(entries):
            label = str(entry.get("legacy_id")) if isinstance(entry, dict) \
                else "#" + str(index)
            for field, message in check_entry(entry, schema):
                problems.append(problem(
                    FAMILY_SCHEMA, name, label, field, message))


def collect_ids(loaded, problems):
    """Per-file uniqueness plus distinctness across the items union."""
    per_file = {}
    for name in sorted(FILE_MAP):
        if name not in loaded:
            continue
        seen = set()
        ids = []
        for index, entry in enumerate(loaded[name]["entries"]):
            if not isinstance(entry, dict):
                continue
            legacy_id = entry.get("legacy_id")
            if legacy_id is None:
                continue
            if legacy_id in seen:
                problems.append(problem(
                    FAMILY_DEPENDENCY, name, legacy_id, "legacy_id",
                    "duplicate legacy_id in file"))
            seen.add(legacy_id)
            ids.append(legacy_id)
        per_file[name] = ids
    union = {}
    for name in ITEM_FILES:
        if name not in per_file:
            continue
        for legacy_id in per_file[name]:
            other = union.get(legacy_id)
            if other is not None and other != name:
                problems.append(problem(
                    FAMILY_DEPENDENCY, "items-union", legacy_id,
                    "legacy_id",
                    "id appears in both %s and %s" % (other, name)))
            else:
                union[legacy_id] = name
    inventory = set(per_file.get(INVENTORY_FILE, []))
    return per_file, union, inventory


def check_item_relations(loaded, union_ids, inventory_ids, problems, stats):
    entries = []
    for name in ITEM_FILES:
        if name in loaded:
            entries.extend(
                (name, entry) for entry in loaded[name]["entries"]
                if isinstance(entry, dict))
    for name, entry in entries:
        legacy_id = entry.get("legacy_id")
        for field in ("upgrades_to", "trains_ids"):
            if field not in entry:
                continue
            value = entry[field]
            if value in RELATION_NONE:
                continue
            stats["references_checked"] += 1
            if str(value) not in union_ids:
                problems.append(problem(
                    FAMILY_DEPENDENCY, name, legacy_id, field,
                    "unresolvable %s: %r" % (field, value)))
        raw_inventory = entry.get("inventory_ids")
        if isinstance(raw_inventory, dict):
            for key in raw_inventory:
                stats["references_checked"] += 1
                if key not in inventory_ids:
                    problems.append(problem(
                        FAMILY_DEPENDENCY, name, legacy_id, "inventory_ids",
                        "unresolvable inventory_ids key: %r" % (key,)))


def check_collections(loaded, union_ids, problems, stats):
    name = "collections.json"
    if name not in loaded:
        return
    for entry in loaded[name]["entries"]:
        if not isinstance(entry, dict):
            continue
        legacy_id = entry.get("legacy_id")
        item_ids = entry.get("item_ids")
        derived_items = None
        if isinstance(item_ids, list):
            derived_items = [str(value) for value in item_ids]
        item_refs = entry.get("item_refs")
        if derived_items is not None and item_refs != derived_items:
            problems.append(problem(
                FAMILY_DEPENDENCY, name, legacy_id, "item_refs",
                "derived %r, stored %r" % (derived_items, item_refs)))
        prize = entry.get("prize")
        prize_refs = entry.get("prize_refs")
        if isinstance(prize, dict):
            derived_prize = sorted(prize.keys())
            if prize_refs != derived_prize:
                problems.append(problem(
                    FAMILY_DEPENDENCY, name, legacy_id, "prize_refs",
                    "derived %r, stored %r" % (derived_prize, prize_refs)))
        for field, values in (("item_refs", item_refs),
                              ("prize_refs", prize_refs)):
            if not isinstance(values, list):
                continue
            for value in values:
                stats["references_checked"] += 1
                if value not in union_ids:
                    problems.append(problem(
                        FAMILY_DEPENDENCY, name, legacy_id, field,
                        "unresolvable reference: %r" % (value,)))


def check_ranking(loaded, union_ids, problems, stats):
    name = "level_ranking_reward.json"
    if name not in loaded:
        return
    for entry in loaded[name]["entries"]:
        if not isinstance(entry, dict):
            continue
        legacy_id = entry.get("legacy_id")
        units = entry.get("units")
        unit_refs = entry.get("unit_refs")
        if isinstance(units, dict):
            derived = sorted(units.keys())
            if unit_refs != derived:
                problems.append(problem(
                    FAMILY_DEPENDENCY, name, legacy_id, "unit_refs",
                    "derived %r, stored %r" % (derived, unit_refs)))
        if isinstance(unit_refs, list):
            for value in unit_refs:
                stats["references_checked"] += 1
                if value not in union_ids:
                    problems.append(problem(
                        FAMILY_DEPENDENCY, name, legacy_id, "unit_refs",
                        "unresolvable reference: %r" % (value,)))


def check_unit_collections(loaded, union_ids, problems, stats):
    name = "unit_collection_categories.json"
    if name not in loaded:
        return
    for entry in loaded[name]["entries"]:
        if not isinstance(entry, dict):
            continue
        legacy_id = entry.get("legacy_id")
        units = entry.get("units")
        unit_refs = entry.get("unit_refs")
        if isinstance(units, list):
            derived = [str(value) for value in units]
            if unit_refs != derived:
                problems.append(problem(
                    FAMILY_DEPENDENCY, name, legacy_id, "unit_refs",
                    "derived %r, stored %r" % (derived, unit_refs)))
        if isinstance(unit_refs, list):
            for value in unit_refs:
                stats["references_checked"] += 1
                if value not in union_ids:
                    problems.append(problem(
                        FAMILY_DEPENDENCY, name, legacy_id, "unit_refs",
                        "unresolvable reference: %r" % (value,)))


def check_darts(loaded, union_ids, problems, stats):
    name = "darts_items.json"
    if name not in loaded:
        return
    for entry in loaded[name]["entries"]:
        if not isinstance(entry, dict):
            continue
        legacy_id = entry.get("legacy_id")
        items = entry.get("items")
        item_refs = entry.get("item_refs")
        if isinstance(items, list):
            derived = [str(value) for value in items]
            if item_refs != derived:
                problems.append(problem(
                    FAMILY_DEPENDENCY, name, legacy_id, "item_refs",
                    "derived %r, stored %r" % (derived, item_refs)))
        extra_item = entry.get("extra_item")
        extra_ref = entry.get("extra_ref")
        if "extra_item" in entry and extra_ref != str(extra_item):
            problems.append(problem(
                FAMILY_DEPENDENCY, name, legacy_id, "extra_ref",
                "derived %r, stored %r" % (str(extra_item), extra_ref)))
        for field, values in (("item_refs", item_refs),):
            if not isinstance(values, list):
                continue
            for value in values:
                stats["references_checked"] += 1
                if value not in union_ids:
                    problems.append(problem(
                        FAMILY_DEPENDENCY, name, legacy_id, field,
                        "unresolvable reference: %r" % (value,)))
        if extra_ref is not None:
            stats["references_checked"] += 1
            if extra_ref not in union_ids:
                problems.append(problem(
                    FAMILY_DEPENDENCY, name, legacy_id, "extra_ref",
                    "unresolvable reference: %r" % (extra_ref,)))


def check_offers(loaded, union_ids, problems, stats):
    name = "offer_packs.json"
    if name not in loaded:
        return
    for entry in loaded[name]["entries"]:
        if not isinstance(entry, dict):
            continue
        legacy_id = entry.get("legacy_id")
        label = "offer " + str(legacy_id)
        derived, derivation_problems = derive_offer_refs(
            entry, union_ids, label)
        item_refs = entry.get("item_refs")
        for field, message in derivation_problems:
            stats["references_checked"] += 1
            problems.append(problem(
                FAMILY_DEPENDENCY, name, legacy_id, field, message))
        if item_refs != derived:
            problems.append(problem(
                FAMILY_DEPENDENCY, name, legacy_id, "item_refs",
                "derived %r, stored %r" % (derived, item_refs)))
        for field, message in check_offer_anomalies(entry):
            problems.append(problem(
                FAMILY_DEPENDENCY, name, legacy_id, field, message))


def check_categories(loaded, problems, stats):
    name = "categories.json"
    if name not in loaded:
        return
    for entry in loaded[name]["entries"]:
        if not isinstance(entry, dict):
            continue
        legacy_id = entry.get("legacy_id")
        category_id = entry.get("id")
        sub = entry.get("sub")
        if not isinstance(sub, list):
            continue
        for index, item in enumerate(sub):
            field = "sub[%d].parent" % index
            if not isinstance(item, dict):
                problems.append(problem(
                    FAMILY_DEPENDENCY, name, legacy_id, field,
                    "sub entry is not an object"))
                continue
            parent = item.get("parent")
            stats["references_checked"] += 1
            if not is_native_int(parent):
                problems.append(problem(
                    FAMILY_DEPENDENCY, name, legacy_id, field,
                    "sub parent not native integer: %r" % (parent,)))
            elif parent != category_id:
                problems.append(problem(
                    FAMILY_DEPENDENCY, name, legacy_id, field,
                    "sub parent %r does not equal category id %r"
                    % (parent, category_id)))


def validate(repo_root):
    """Run every check; returns (problems, success_report_or_None)."""
    package = repo_root.joinpath(*PACKAGE_REL)
    manifest_path = package / "manifest.json"
    if not manifest_path.is_file():
        raise InvalidInput("missing manifest.json")
    manifest = load_json_file(manifest_path, "manifest.json")
    if not isinstance(manifest, dict):
        raise InvalidInput("manifest.json is not a json object")

    problems = []
    check_record_fields(manifest, problems)
    loaded, recorded = read_outputs(repo_root, manifest, problems)
    check_directory_hygiene(repo_root, recorded, problems)
    check_counts(loaded, problems)
    schemas = check_schemas(repo_root, problems)
    check_entries(loaded, schemas, problems)

    stats = {"references_checked": 0}
    per_file, union_ids, inventory_ids = collect_ids(loaded, problems)
    check_item_relations(
        loaded, union_ids, inventory_ids, problems, stats)
    check_collections(loaded, union_ids, problems, stats)
    check_ranking(loaded, union_ids, problems, stats)
    check_unit_collections(loaded, union_ids, problems, stats)
    check_darts(loaded, union_ids, problems, stats)
    check_offers(loaded, union_ids, problems, stats)
    check_categories(loaded, problems, stats)

    problems.sort(key=problem_sort_key)
    if problems:
        return problems, None
    report = {
        "result": "valid",
        "files_verified": len(loaded),
        "schemas_verified": len(schemas),
        "counts_checked": len(FILE_MAP),
        "references_checked": stats["references_checked"],
        "entries": {
            name: len(loaded[name]["entries"]) for name in sorted(FILE_MAP)
            if name in loaded
        },
    }
    return [], report


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    try:
        repo_root = parse_args(argv)
    except InvalidInput as error:
        sys.stderr.write(str(error) + "\n")
        return 2
    if repo_root is None:
        print(USAGE)
        return 0
    root = Path(repo_root)
    try:
        problems, report = validate(root)
    except InvalidInput as error:
        sys.stderr.write("invalid input: " + str(error) + "\n")
        return 2
    if problems:
        print(json.dumps(
            {"result": "validation-failed", "problems": problems},
            sort_keys=True, indent=2))
        return 1
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
