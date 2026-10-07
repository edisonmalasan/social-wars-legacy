"""Offline auction-schedule normalization builder and validator.

Loads the standalone committed auction table (`config/auctionhouse.json`, 3
entries, one top-level `auctions` array) and emits one normalized definition
per committed entry in committed order, preserving every committed value
verbatim per the documented auction coercion ruleset:

  * `uuid` stays the committed JSON **string** and becomes `legacy_id`
    verbatim. It is not coerced to an integer: the legacy module keys its
    state document by that value (`auctions.py:106`) and the committed table
    declares it quoted, so an integer would claim a type the source does not
    carry (rule A1).
  * `interval` is preserved verbatim in its committed unit, **minutes**, and
    is **not** converted. The single conversion the legacy module performs
    (`seconds = auction["interval"] * 60`, `auctions.py:76`) belongs to the
    consuming client, where it lives in one named function; the factor `60`
    is deliberately not recorded as data here (rule A2).
  * `unit` is resolved against the committed normalized units package (the
    cross-domain reference edge every sibling builder uses) and the resolved
    display name is carried. An unresolvable id is **recorded as
    unresolved**, still emitted, in committed order, and reported on stdout
    and in the manifest counts -- never dropped, replaced or invented
    (rule A3).
  * `betPrice` is carried verbatim together with `bet_price_consumed: false`.
    That flag is not an assertion that the price is meaningless: the module
    text is read (never imported, never executed) and measured for the
    resource tokens it contains. `betPrice` is written into state at
    `auctions.py:97` and `auctions.py:137` and read nowhere (rule A4).

The content source is the standalone file `config/auctionhouse.json`. It is
**not** one of the 20 top-level keys of `config/main.json`, so no patch
layering, no stored/patched split and no mods pipeline apply to this table;
the loader instead refuses any top-level shape other than exactly the
`auctions` array.

The builder SHALL NOT import or execute `auctions.py` (design D3). Importing
it would run `__init__`, which calls `os.makedirs` on a path relative to the
process cwd and so would create an `auctions/` state directory as a side
effect of reading committed content. The module's bytes are only ever read
as text and counted; nothing from it is executed.

On success the normalized auction package (`normalized/auctions.json`, plus
the `auctions` section merged into `manifest.json`) is written and exit 0 with
a JSON report on stdout is returned. Any validation failure exits 1 without
writing output. Invalid input or unsupported shapes exit 2. Standard library
only: no legacy application import, no runtime save reads, no network, server,
browser, Flash, or wall-clock activity.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

COERCION_RULESET_VERSION = "auction-coercion-ruleset-v1"
POLICY = "auction-normalization-v1"

AUCTION_CONFIG_FILE = Path("config") / "auctionhouse.json"
LEGACY_MODULE_FILE = Path("auctions.py")
SCHEMA_DIR = Path("packages") / "game-content" / "schemas"
AUCTION_SCHEMA_FILE = SCHEMA_DIR / "auction.schema.json"
NORMALIZED_DIR = Path("packages") / "game-content" / "normalized"
UNITS_FILE = NORMALIZED_DIR / "units.json"
AUCTIONS_FILE = NORMALIZED_DIR / "auctions.json"
MANIFEST_FILE = Path("packages") / "game-content" / "manifest.json"

MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_KEYS = 64
MAX_AUCTION_ENTRIES = 4096

# Committed auction field set. Anything else is content drift.
AUCTION_FIELDS = (
    "uuid",
    "unit",
    "level",
    "interval",
    "price",
    "priceIncrement",
    "betPrice",
)

AUCTIONS_KEY = "auctions"

KIND = "auction"
SOURCE_LAYER = "stored"

# Rule A2: the committed interval unit, carried as a label so a reader cannot
# mistake the value for seconds. The conversion factor is deliberately absent.
INTERVAL_UNIT = "minutes"

# Rule A4: the tokens measured against the legacy module text to establish
# that betPrice has no consumer. Whole-token counting is the rule; the
# substring count is recorded beside it because one token (xp) is a substring
# artifact of `expired`, which a substring scan alone would misreport as a
# consumer.
BET_PRICE_RESOURCE_TOKENS = (
    "gold",
    "coins",
    "cash",
    "wood",
    "steel",
    "oil",
    "xp",
    "mana",
    "energy",
    "cost",
    "apply_resources",
)

# Where the committed betPrice is written into the legacy state document.
BET_PRICE_WRITE_SITES = ("auctions.py:97", "auctions.py:137")

WORD_PATTERN = r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])"


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


def load_schema(root, filename, kind):
    """Load the schema and enforce its own structural contract.

    The schema must be an object schema whose `required` fields all appear in
    `properties`, whose `kind` const matches this builder's kind, and whose
    explicit `x-coercion-ruleset` block lists a rule for **every** committed
    field. A coercion that cannot be listed is not permitted, so the ruleset
    is a load-time gate rather than documentation (rule A1).
    """
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
            raise InputError("schema invalid, required not in properties: "
                             + filename)
    kind_spec = properties.get("kind")
    if not isinstance(kind_spec, dict) or kind_spec.get("const") != kind:
        raise InputError("schema invalid, kind const mismatch: " + filename)
    validate_coercion_ruleset(schema, filename)
    return schema


def validate_coercion_ruleset(schema, filename):
    """Enforce the explicit coercion ruleset carried inside the schema.

    Every committed field must appear in at least one rule, every rule's
    committed field must be a committed field, every rule's normalized field
    must exist in the schema properties, and every normalized field that is
    not produced by a rule must be listed in `non_committed_fields` with a
    named derivation. An unlisted transformation is therefore impossible to
    ship rather than merely undocumented.
    """
    ruleset = schema.get("x-coercion-ruleset")
    if not isinstance(ruleset, dict):
        raise InputError("schema coercion ruleset missing: " + filename)
    if ruleset.get("version") != COERCION_RULESET_VERSION:
        raise InputError("schema coercion ruleset version mismatch: "
                         + filename)
    rules = ruleset.get("rules")
    if not isinstance(rules, list) or not rules:
        raise InputError("schema coercion ruleset rules missing: " + filename)
    properties = schema["properties"]
    listed_committed = set()
    listed_normalized = set()
    for position, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise InputError("schema coercion rule not object at position "
                             + str(position) + ": " + filename)
        committed = rule.get("committed_field")
        normalized = rule.get("normalized_field")
        transform = rule.get("transform")
        if committed not in AUCTION_FIELDS:
            raise InputError("schema coercion rule names an uncommitted field "
                             + repr(committed) + " at position "
                             + str(position) + ": " + filename)
        if not isinstance(normalized, str) or normalized not in properties:
            raise InputError("schema coercion rule normalized_field not in "
                             "properties at position " + str(position) + ": "
                             + filename)
        if not isinstance(transform, str) or not transform:
            raise InputError("schema coercion rule transform missing at "
                             "position " + str(position) + ": " + filename)
        listed_committed.add(committed)
        listed_normalized.add(normalized)
    missing = sorted(set(AUCTION_FIELDS) - listed_committed)
    if missing:
        raise InputError("schema coercion ruleset omits committed fields: "
                         + ", ".join(missing) + "; " + filename)
    non_committed = ruleset.get("non_committed_fields")
    if not isinstance(non_committed, dict):
        raise InputError("schema coercion ruleset non_committed_fields "
                         "missing: " + filename)
    unlisted = sorted(set(properties) - listed_normalized)
    for field in unlisted:
        entry = non_committed.get(field)
        if not isinstance(entry, dict):
            raise InputError("normalized field with no listed derivation: "
                             + field + "; " + filename)
        if not isinstance(entry.get("derivation"), str) \
                or not entry["derivation"]:
            raise InputError("non-committed field without a named derivation: "
                             + field + "; " + filename)
    for field in sorted(non_committed):
        if field in listed_normalized:
            raise InputError("field listed both as a coercion target and as "
                             "non-committed: " + field + "; " + filename)


def load_units_reference(root):
    """Read the committed normalized units package: the reference edge.

    Returns ({legacy_id: name}, {"units": count}). The committed table names
    units, so the edge is the units file alone -- not the buildings/specials
    union the sibling builders use, because that union would let a building
    id resolve as a unit and silently satisfy an auction that names no unit.
    """
    text = read_text_file(root / UNITS_FILE, "normalized units")
    try:
        entries = json.loads(text)
    except ValueError:
        raise InputError("normalized units file not valid json: "
                         + UNITS_FILE.as_posix())
    if not isinstance(entries, list) or not entries:
        raise InputError("normalized units file not non-empty array: "
                         + UNITS_FILE.as_posix())
    names = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise InputError("normalized units entry not object: "
                             + UNITS_FILE.as_posix())
        legacy_id = entry.get("legacy_id")
        if not isinstance(legacy_id, str) or not legacy_id:
            raise InputError("normalized units entry missing legacy_id: "
                             + UNITS_FILE.as_posix())
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            raise InputError("normalized units entry missing name: "
                             + UNITS_FILE.as_posix())
        if legacy_id in names:
            raise InputError("normalized units duplicate legacy_id: "
                             + legacy_id)
        names[legacy_id] = name
    return names, {"units": len(entries)}


def count_words(source_text, token):
    """Whole-token occurrences; a token inside a longer name is not a hit."""
    return len(re.findall(WORD_PATTERN % re.escape(token), source_text))


def measure_bet_price_consumers(source_text):
    """Rule A4: measure the legacy module for any resource consumer.

    The module text is read as bytes and counted. It is never imported and
    never executed, so no module-level side effect is reachable (design D3).
    Both the whole-token count and the raw substring count are recorded: the
    rule is the whole-token count, and the substring count is kept beside it
    because `xp` is a substring of `expired`/`count_expired` and a
    substring-only scan would report a consumer that does not exist.
    """
    whole = {}
    substring = {}
    artifacts = {}
    for token in BET_PRICE_RESOURCE_TOKENS:
        hits = count_words(source_text, token)
        whole[token] = hits
        substring[token] = source_text.count(token)
        if substring[token] != hits:
            found = sorted(set(re.findall(r"[A-Za-z0-9_]*" + re.escape(token)
                                          + r"[A-Za-z0-9_]*", source_text)))
            artifacts[token] = found
    called = sorted(set(re.findall(r"self\.([A-Za-z_][A-Za-z0-9_]*)\s*\(",
                                   source_text)))
    return {
        "resource_tokens_whole_token": whole,
        "resource_tokens_substring": substring,
        "resource_token_substring_artifacts": artifacts,
        "self_called_methods": len(called),
        "apply_resources_called": "apply_resources" in called,
        "bet_price_write_sites": list(BET_PRICE_WRITE_SITES),
        "consumed": any(whole.values()) or "apply_resources" in called,
        "counting_rule": (
            "whole-token occurrence in the module text, never a substring: "
            "one token (xp) is a substring artifact of expired/count_expired "
            "and is recorded beside the whole-token count so the two cannot "
            "be confused"
        ),
    }


def coerce_auction(raw, label):
    """Coerce one committed auction entry per rules A1/A2 (verbatim).

    No value is parsed, defaulted, padded or converted. `uuid` is required to
    be a committed JSON string; accepting an integer here would be the
    transformation rule A1 forbids.
    """
    if not isinstance(raw, dict):
        raise ValidationFailure(["entry not object: " + label])
    problems = []
    for field in AUCTION_FIELDS:
        if field not in raw:
            problems.append("missing field: " + label + "." + field)
    for field in raw:
        if field not in AUCTION_FIELDS:
            problems.append("unexpected field: " + label + "." + field)
    if problems:
        raise ValidationFailure(problems)
    uuid = raw["uuid"]
    if not isinstance(uuid, str) or not uuid:
        raise ValidationFailure(["uuid not non-empty committed string: "
                                 + label + "; rule A1 preserves the committed "
                                 "JSON string and refuses an integer"])
    for field in ("unit", "level", "interval", "price", "priceIncrement",
                  "betPrice"):
        if type(raw[field]) is not int:
            raise ValidationFailure([field + " not native integer: " + label])
    return {
        "uuid": uuid,
        "unit": raw["unit"],
        "level": raw["level"],
        "interval": raw["interval"],
        "price": raw["price"],
        "priceIncrement": raw["priceIncrement"],
        "betPrice": raw["betPrice"],
    }


def build_auction_definition(body, fingerprint, unit_names, consumption):
    """Project one committed entry. `unit` resolution never drops an entry."""
    unit_ref = str(body["unit"])
    resolved = unit_ref in unit_names
    return {
        "legacy_id": body["uuid"],
        "kind": KIND,
        "source_file": AUCTION_CONFIG_FILE.as_posix(),
        "source_layer": SOURCE_LAYER,
        "content_version": fingerprint,
        "uuid": body["uuid"],
        "unit": body["unit"],
        "unit_ref": unit_ref,
        "unit_name": unit_names[unit_ref] if resolved else None,
        "unit_resolved": resolved,
        "level": body["level"],
        "interval": body["interval"],
        "interval_unit": INTERVAL_UNIT,
        "price": body["price"],
        "priceIncrement": body["priceIncrement"],
        "betPrice": body["betPrice"],
        "bet_price_consumed": consumption["consumed"],
    }


def check_schema_type(value, allowed, label, problems):
    """Enforce one JSON-Schema type union; bool never counts as integer."""
    for kind in allowed:
        if kind == "integer" and type(value) is int:
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


def check_unit_references(auctions, unit_names):
    """Rule A3: an unresolvable unit is reported, never dropped.

    Returns the list of reportable strings. It is deliberately not a failure:
    the spec requires the definition to be emitted in committed order with a
    null display name and the failure reported, not the build refused.
    """
    reported = []
    for definition in auctions:
        if definition["unit_resolved"]:
            continue
        if definition["unit_name"] is not None:
            reported.append("inconsistent unresolved unit at auction "
                            + definition["legacy_id"] + ": display name present")
        reported.append("unresolved auction unit reference: auction "
                        + definition["legacy_id"] + " -> " + definition["unit_ref"]
                        + "; definition emitted in committed order with a null"
                        " display name and nothing replaced or invented")
    return reported


def check_round_trip(auctions, stored):
    """Rule A4: diff every committed field of every entry back exactly.

    The comparison covers all 7 committed keys on all 3 committed entries.
    `uuid` is compared as the committed string, so an integer in the source
    would fail here as well as in the coercion.
    """
    problems = []
    if len(auctions) != len(stored):
        problems.append("round-trip auction count mismatch: %d definitions "
                        "vs %d committed"
                        % (len(auctions), len(stored)))
        return problems
    for definition, original in zip(auctions, stored):
        entry_label = "round-trip auction " + definition["legacy_id"]
        if not isinstance(original, dict):
            problems.append(entry_label + ": committed entry not object")
            continue
        try:
            body = coerce_auction(original, "round-trip")
        except ValidationFailure as failure:
            problems.extend([entry_label + ": " + item for item in failure.problems])
            continue
        for field in AUCTION_FIELDS:
            if body[field] != definition[field]:
                problems.append(entry_label + ": drift at " + field)
        if set(original.keys()) != set(AUCTION_FIELDS):
            problems.append(entry_label + ": field-set drift "
                            + repr(sorted(set(original.keys())
                                          ^ set(AUCTION_FIELDS))))
    return problems


def load_all(root):
    """Load the standalone committed auction table and its reference edge.

    No patch layering, no mods pipeline and no `config/main.json` read: this
    table is not one of that document's 20 top-level keys, so any top-level
    shape other than exactly the `auctions` array is refused as drift.
    """
    root = Path(root)
    if not root.is_dir():
        raise InputError("repository root invalid: " + str(root))
    config_bytes = read_bytes_file(root / AUCTION_CONFIG_FILE, "auction config")
    try:
        document = json.loads(config_bytes.decode("utf-8"))
    except ValueError:
        raise InputError("auction config file not valid json")
    if not isinstance(document, dict) or not document:
        raise InputError("unsupported auction config shape: top level not object")
    if len(document) > MAX_TOTAL_KEYS:
        raise InputError("auction config key limit exceeded")
    if set(document.keys()) != {AUCTIONS_KEY}:
        raise InputError("unsupported auction config shape: expected exactly "
                         "the auctions key, found "
                         + repr(sorted(document.keys()))
                         + "; the standalone table carries no other key")
    if not isinstance(document[AUCTIONS_KEY], list) or not document[AUCTIONS_KEY]:
        raise InputError("unsupported auction config shape: auctions not "
                         "non-empty array")
    if len(document[AUCTIONS_KEY]) > MAX_AUCTION_ENTRIES:
        raise InputError("auction entry limit exceeded")
    units_bytes = read_bytes_file(root / UNITS_FILE, "normalized units")
    unit_names, units_counts = load_units_reference(root)
    module_bytes = read_bytes_file(root / LEGACY_MODULE_FILE, "legacy auction module")
    try:
        module_text = module_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise InputError("legacy auction module not utf-8")
    consumption = measure_bet_price_consumers(module_text)
    manifest_text = read_text_file(root / MANIFEST_FILE, "package manifest")
    try:
        manifest_document = json.loads(manifest_text)
    except ValueError:
        raise InputError("package manifest not valid json")
    if not isinstance(manifest_document, dict):
        raise InputError("package manifest not object")
    return {
        "stored_auctions": document[AUCTIONS_KEY],
        "unit_names": unit_names,
        "units_counts": units_counts,
        "consumption": consumption,
        "manifest": manifest_document,
        "config_bytes": config_bytes,
        "units_bytes": units_bytes,
        "module_bytes": module_bytes,
    }


def fingerprint_inputs(layers):
    """Content fingerprint over the committed bytes this builder reads."""
    digest = hashlib.sha256()
    digest.update(layers["config_bytes"])
    digest.update(layers["units_bytes"])
    return digest.hexdigest()


def build_package(repo_root, out_root):
    """Build in memory, validate everything, then write output files."""
    root = Path(repo_root)
    layers = load_all(root)
    fingerprint = fingerprint_inputs(layers)
    stored = layers["stored_auctions"]
    consumption = layers["consumption"]
    problems = []
    bodies = []
    for entry in stored:
        label = ("auction uuid " + repr(entry.get("uuid"))
                 if isinstance(entry, dict) else "auction entry")
        try:
            bodies.append(coerce_auction(entry, label))
        except ValidationFailure as failure:
            problems.extend(failure.problems)
    if problems:
        raise ValidationFailure(problems)
    auctions = [build_auction_definition(body, fingerprint,
                                         layers["unit_names"], consumption)
                for body in bodies]
    if len({item["legacy_id"] for item in auctions}) != len(auctions):
        raise ValidationFailure(["duplicate auction uuid in committed table"])
    reported = check_unit_references(auctions, layers["unit_names"])
    auction_schema = load_schema(root, AUCTION_SCHEMA_FILE.name, KIND)
    for item in auctions:
        problems.extend(validate_against_schema(
            item, auction_schema, "auction " + item["legacy_id"]))
    if problems:
        raise ValidationFailure(problems)
    round_problems = check_round_trip(auctions, stored)
    if round_problems:
        raise ValidationFailure(round_problems)
    resolved = sum(1 for item in auctions if item["unit_resolved"])
    files = {AUCTIONS_FILE: auctions}
    auctions_section = {
        "schema_version": 1,
        "policy": POLICY,
        "result": "success",
        "inputs": {
            "auctionhouse": {
                "file": AUCTION_CONFIG_FILE.as_posix(),
                "bytes": len(layers["config_bytes"]),
                "sha256": hashlib.sha256(layers["config_bytes"]).hexdigest(),
            },
            "content_source": (
                "standalone committed file, not one of the 20 top-level keys "
                "of config/main.json; no patch layering and no mods pipeline "
                "apply to this table"
            ),
            "units_reference_edge": {
                "file": UNITS_FILE.as_posix(),
                "counts": dict(layers["units_counts"]),
                "union_legacy_ids": len(layers["unit_names"]),
            },
            "legacy_module_measurement": {
                "file": LEGACY_MODULE_FILE.as_posix(),
                "bytes": len(layers["module_bytes"]),
                "sha256": hashlib.sha256(layers["module_bytes"]).hexdigest(),
                "read_as_text_only": True,
                "imported": False,
                "executed": False,
                **layers["consumption"],
            },
        },
        "coercion_ruleset": COERCION_RULESET_VERSION,
        "content_fingerprint": fingerprint,
        "counts": {
            "stored_auctions": len(stored),
            "auctions": len(auctions),
            "levels": sorted({item["level"] for item in auctions}),
            "intervals": sorted({item["interval"] for item in auctions}),
            "interval_unit": INTERVAL_UNIT,
            "bet_prices": sorted({item["betPrice"] for item in auctions}),
            "resolved_units": resolved,
            "unresolved_units": len(auctions) - resolved,
        },
        "validation": {
            "duplicate_ids": 0,
            "missing_fields": 0,
            "round_trip_diffs": 0,
            "unresolved_unit_references": len(auctions) - resolved,
            "bet_price_consumers": sum(
                layers["consumption"]["resource_tokens_whole_token"].values())
            + (1 if layers["consumption"]["apply_resources_called"] else 0),
        },
        "reported": reported,
        "outputs": [],
        "notes": [
            "One definition per committed entry in committed order; nothing "
            "is added, removed, merged or deduplicated (rule A1).",
            "legacy_id is the committed uuid JSON string verbatim; an integer "
            "would claim a type the source does not carry, and the legacy "
            "module keys its state document by that value (auctions.py:106) "
            "(rule A1).",
            "interval is preserved in its committed unit, minutes, and is not "
            "converted; the single conversion the legacy module performs "
            "(seconds = auction[\"interval\"] * 60, auctions.py:76) belongs to "
            "the consuming client, and the factor 60 is deliberately not "
            "recorded as data here (rule A2).",
            "unit resolves against normalized/units.json and the resolved "
            "display name is carried; an unresolvable id is emitted in "
            "committed order with a null name and reported, never dropped, "
            "replaced or invented (rule A3).",
            "betPrice is carried verbatim and marked bet_price_consumed "
            "false beside the measured zero-consumer record: the module text "
            "holds zero whole-token occurrences of gold, coins, cash, wood, "
            "steel, oil, xp, mana, energy, cost or apply_resources and never "
            "calls apply_resources. betPrice is written into state at "
            "auctions.py:97 and auctions.py:137 and read nowhere (rule A4).",
            "The legacy module is read as text for that measurement and is "
            "never imported or executed, because importing it would run an "
            "__init__ that creates an auctions/ state directory as a side "
            "effect of reading committed content (design D3).",
            "No price, fee, total, remaining time, round, winner or ranking is "
            "derived, and no committed value is converted, defaulted or padded.",
        ],
    }
    payloads = {}
    for path, entries in files.items():
        payloads[path] = json.dumps(entries, indent=2) + "\n"
    return auctions_section, payloads


def write_outputs(out_root, auctions_section, payloads):
    # Byte-exact writes: payloads are encoded once and the same bytes feed
    # the digest records. The auctions section is merged into the existing
    # package manifest (prior keys preserved byte for byte under sort_keys);
    # the manifest cannot digest itself, so only the normalized auctions file
    # is digested.
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
    auctions_section["outputs"] = outputs
    manifest_path = out / MANIFEST_FILE
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise InputError("package manifest not object")
    manifest["auctions"] = auctions_section
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
    auctions_section, payloads = build_package(repo_root, out_root)
    manifest = write_outputs(out_root, auctions_section, payloads)
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
    section = manifest["auctions"]
    report = {
        "schema_version": 1,
        "policy": POLICY,
        "result": "success",
        "counts": section["counts"],
        "outputs": [entry["file"] for entry in section["outputs"]],
        "reported": section["reported"],
        "problems": [],
    }
    print(json.dumps(report, indent=2, sort_keys=True) + "\n", end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())