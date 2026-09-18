"""Offline read-only legacy content field-type survey verification.

Compares the reviewed field-type survey (`docs/game-content/field-types.json`)
and its readable survey (`docs/game-content/field-types.md`) against the stored
content source `config/main.json`.

Only structural parsing with the standard library is used. The legacy
application is never imported, runtime saves are never read, and no network,
server, browser, or Flash activity occurs. Exit 0 agreement, 1 survey drift,
2 invalid input or unsupported content shape. Standard library only.
"""

import argparse
import json
import re
from pathlib import Path
import sys

MAIN_CONFIG_FILE = Path("config") / "main.json"
SURVEY_FILE = Path("docs") / "game-content" / "field-types.json"
READABLE_FILE = Path("docs") / "game-content" / "field-types.md"
MAX_SOURCE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_KEYS = 64

# Deterministic numeric grammar for the string-encoded-number predicate:
# optional sign, digits with an optional fraction (or a leading-dot fraction),
# and an optional decimal exponent. No surrounding whitespace, no hex, no
# thousands separators, and no Infinity/NaN spellings are accepted.
NUMERIC_GRAMMAR = r"[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
NUMERIC_PATTERN = re.compile(NUMERIC_GRAMMAR)

VALUE_TYPES = ("string", "number", "boolean", "null", "array", "object")
ENCODING_CLASSES = ("string_encoded", "native", "mixed")


class VerificationError(Exception):
    pass


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


def classify_json_value(value):
    if isinstance(value, str):
        return "string"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if value is None:
        return "null"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    raise VerificationError("unsupported content shape: non-json value")


def read_text_file(path, role):
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        raise VerificationError(role + " file missing")
    except OSError:
        raise VerificationError(role + " file unreadable")
    if len(data) > MAX_SOURCE_BYTES:
        raise VerificationError(role + " file too large")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise VerificationError(role + " file not utf-8")


def load_main_config(path):
    text = read_text_file(path, "content")
    try:
        document = json.loads(text)
    except ValueError:
        raise VerificationError("content file not valid json")
    if not isinstance(document, dict):
        raise VerificationError("unsupported content shape: top level is not an object")
    if not document:
        raise VerificationError("unsupported content shape: top level object is empty")
    if len(document) > MAX_TOTAL_KEYS:
        raise VerificationError("content key limit exceeded")
    for key, value in document.items():
        if not isinstance(key, str) or not key:
            raise VerificationError("unsupported content shape: empty content key")
        if not isinstance(value, (list, dict)):
            raise VerificationError(
                "unsupported content shape: content key " + key)
    return document


def profile_array_key(entries):
    fields = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise VerificationError(
                "unsupported content shape: array entry is not an object")
        for name, value in entry.items():
            profile = fields.get(name)
            if profile is None:
                profile = {"presence_count": 0, "types": {kind: 0 for kind in VALUE_TYPES},
                           "string_encoded_number_count": 0,
                           "embedded_json_string_count": 0,
                           "empty_string_count": 0, "null_count": 0}
                fields[name] = profile
            profile["presence_count"] += 1
            profile["types"][classify_json_value(value)] += 1
            if isinstance(value, str):
                if value == "":
                    profile["empty_string_count"] += 1
                if is_string_encoded_number(value):
                    profile["string_encoded_number_count"] += 1
                if is_embedded_json_string(value):
                    profile["embedded_json_string_count"] += 1
            elif value is None:
                profile["null_count"] += 1
    return fields


def profile_object_key(entries):
    distribution = {kind: 0 for kind in VALUE_TYPES}
    for value in entries.values():
        distribution[classify_json_value(value)] += 1
    return distribution


def extract_survey(document):
    array_keys = {}
    object_keys = {}
    for key, value in document.items():
        if isinstance(value, list):
            array_keys[key] = {"entry_count": len(value),
                               "fields": profile_array_key(value)}
        else:
            object_keys[key] = {"entry_count": len(value),
                                "value_types": profile_object_key(value)}
    whole = {"string_count": 0, "number_count": 0,
             "boolean_count": 0, "null_count": 0}

    def walk(value):
        kind = classify_json_value(value)
        if kind == "string":
            whole["string_count"] += 1
        elif kind == "number":
            whole["number_count"] += 1
        elif kind == "boolean":
            whole["boolean_count"] += 1
        elif kind == "null":
            whole["null_count"] += 1
        elif kind == "array":
            for item in value:
                walk(item)
        elif kind == "object":
            for item in value.values():
                walk(item)

    walk(document)
    return array_keys, object_keys, whole


def _require_non_empty_string(value):
    return isinstance(value, str) and bool(value)


def _require_source_references(value):
    if not isinstance(value, list) or not value:
        return False
    for reference in value:
        if not isinstance(reference, dict):
            return False
        if not _require_non_empty_string(reference.get("file")):
            return False
        line = reference.get("line")
        end_line = reference.get("end_line")
        if type(line) is not int or line < 1:
            return False
        if type(end_line) is not int or end_line < line:
            return False
    return True


def _require_field_profile(profile, label):
    if not isinstance(profile, dict):
        raise VerificationError("survey schema invalid: " + label)
    if type(profile.get("presence_count")) is not int or profile["presence_count"] < 0:
        raise VerificationError("survey schema invalid: " + label)
    types = profile.get("types")
    if not isinstance(types, dict) or set(types) != set(VALUE_TYPES):
        raise VerificationError("survey schema invalid: " + label)
    for kind, count in types.items():
        if type(count) is not int or count < 0:
            raise VerificationError("survey schema invalid: " + label)
    if sum(types.values()) != profile["presence_count"]:
        raise VerificationError("survey schema invalid: " + label)
    for field in ("string_encoded_number_count", "embedded_json_string_count",
                  "empty_string_count", "null_count"):
        if type(profile.get(field)) is not int or profile[field] < 0:
            raise VerificationError("survey schema invalid: " + label)
    if profile["null_count"] != types["null"]:
        raise VerificationError("survey schema invalid: " + label)
    string_count = types["string"]
    for field in ("string_encoded_number_count", "embedded_json_string_count",
                  "empty_string_count"):
        if profile[field] > string_count:
            raise VerificationError("survey schema invalid: " + label)


def load_survey(path):
    text = read_text_file(path, "survey")
    try:
        document = json.loads(text)
    except ValueError:
        raise VerificationError("survey file not valid json")
    if not isinstance(document, dict):
        raise VerificationError("survey file not valid json")
    if document.get("schema_version") != 1:
        raise VerificationError("survey schema invalid")
    policy = document.get("policy")
    if not isinstance(policy, dict):
        raise VerificationError("survey schema invalid")
    for field in ("survey_id", "source_file", "evidence_policy", "count_note"):
        if not _require_non_empty_string(policy.get(field)):
            raise VerificationError("survey schema invalid: policy field " + field)
    for field in ("key_count", "array_key_count", "object_key_count"):
        if type(policy.get(field)) is not int or policy[field] < 0:
            raise VerificationError("survey schema invalid: policy field " + field)
    predicates = document.get("predicates")
    if not isinstance(predicates, dict):
        raise VerificationError("survey schema invalid")
    numeric = predicates.get("string_encoded_number")
    if not isinstance(numeric, dict):
        raise VerificationError("survey schema invalid")
    if numeric.get("grammar") != NUMERIC_GRAMMAR:
        raise VerificationError("survey schema invalid: numeric grammar")
    if not _require_non_empty_string(numeric.get("description")):
        raise VerificationError("survey schema invalid: numeric description")
    embedded = predicates.get("embedded_json_string")
    if not isinstance(embedded, dict):
        raise VerificationError("survey schema invalid")
    if not _require_non_empty_string(embedded.get("rule")):
        raise VerificationError("survey schema invalid: embedded rule")
    if not _require_non_empty_string(embedded.get("description")):
        raise VerificationError("survey schema invalid: embedded description")
    whole = document.get("whole_file")
    if not isinstance(whole, dict):
        raise VerificationError("survey schema invalid")
    for field in ("string_count", "number_count", "boolean_count", "null_count"):
        if type(whole.get(field)) is not int or whole[field] < 0:
            raise VerificationError("survey schema invalid: whole_file " + field)
    array_entries = document.get("array_keys")
    if not isinstance(array_entries, list) or not array_entries:
        raise VerificationError("survey schema invalid")
    seen = set()
    for entry in array_entries:
        if not isinstance(entry, dict):
            raise VerificationError("survey schema invalid")
        name = entry.get("name")
        if not _require_non_empty_string(name):
            raise VerificationError("survey schema invalid: array key name")
        if name in seen:
            raise VerificationError("survey schema invalid: duplicate array key")
        seen.add(name)
        if type(entry.get("entry_count")) is not int or entry["entry_count"] < 0:
            raise VerificationError("survey schema invalid: entry_count " + name)
        if entry.get("encoding_class") not in ENCODING_CLASSES:
            raise VerificationError("survey schema invalid: encoding_class " + name)
        fields = entry.get("fields")
        if not isinstance(fields, dict) or not fields:
            raise VerificationError("survey schema invalid: fields " + name)
        for field_name, profile in fields.items():
            if not _require_non_empty_string(field_name):
                raise VerificationError("survey schema invalid: field name " + name)
            _require_field_profile(profile, "field " + name + "." + field_name)
        if "notes" in entry and not isinstance(entry.get("notes"), str):
            raise VerificationError("survey schema invalid: notes " + name)
        if not _require_source_references(entry.get("source_references")):
            raise VerificationError(
                "survey schema invalid: source_references " + name)
    object_entries = document.get("object_keys")
    if not isinstance(object_entries, list) or not object_entries:
        raise VerificationError("survey schema invalid")
    seen_objects = set()
    for entry in object_entries:
        if not isinstance(entry, dict):
            raise VerificationError("survey schema invalid")
        name = entry.get("name")
        if not _require_non_empty_string(name):
            raise VerificationError("survey schema invalid: object key name")
        if name in seen_objects:
            raise VerificationError("survey schema invalid: duplicate object key")
        seen_objects.add(name)
        if type(entry.get("entry_count")) is not int or entry["entry_count"] < 0:
            raise VerificationError("survey schema invalid: entry_count " + name)
        distribution = entry.get("value_types")
        if not isinstance(distribution, dict) or set(distribution) != set(VALUE_TYPES):
            raise VerificationError("survey schema invalid: value_types " + name)
        for kind, count in distribution.items():
            if type(count) is not int or count < 0:
                raise VerificationError("survey schema invalid: value_types " + name)
        if sum(distribution.values()) != entry["entry_count"]:
            raise VerificationError("survey schema invalid: value_types total " + name)
        if "notes" in entry and not isinstance(entry.get("notes"), str):
            raise VerificationError("survey schema invalid: notes " + name)
        if not _require_source_references(entry.get("source_references")):
            raise VerificationError(
                "survey schema invalid: source_references " + name)
    if seen & seen_objects:
        raise VerificationError("survey schema invalid: key in both sections")
    if policy["key_count"] != len(seen) + len(seen_objects):
        raise VerificationError("survey schema invalid: key_count mismatch")
    if policy["array_key_count"] != len(seen):
        raise VerificationError("survey schema invalid: array_key_count mismatch")
    if policy["object_key_count"] != len(seen_objects):
        raise VerificationError("survey schema invalid: object_key_count mismatch")
    return document


def validate_source_references(document, root):
    try:
        anchored = root.resolve()
    except OSError:
        raise VerificationError("repository root invalid")
    blocks = []
    for entry in document["array_keys"]:
        blocks.append((entry["name"], entry.get("source_references", [])))
    for entry in document["object_keys"]:
        blocks.append((entry["name"], entry.get("source_references", [])))
    for label, references in blocks:
        for reference in references:
            name = reference.get("file")
            try:
                resolved = (root / name).resolve()
                resolved.relative_to(anchored)
            except (OSError, ValueError):
                raise VerificationError(
                    "survey source reference outside repository: " + label)
            if not resolved.is_file():
                raise VerificationError(
                    "survey source reference missing: " + label)
            content = read_text_file(resolved, "reference")
            total = len(content.splitlines())
            line = reference["line"]
            end_line = reference["end_line"]
            if not 1 <= line <= end_line <= total:
                raise VerificationError(
                    "survey source reference out of range: " + label)


def check_whole_file(source_whole, document):
    problems = []
    survey_whole = document["whole_file"]
    for field in ("string_count", "number_count", "boolean_count", "null_count"):
        if source_whole[field] != survey_whole[field]:
            problems.append("survey whole-file drift for " + field
                            + " (source " + str(source_whole[field])
                            + ", survey " + str(survey_whole[field]) + ")")
    return problems


def check_key_coverage(source_arrays, source_objects, document):
    problems = []
    survey_arrays = {entry["name"]: entry for entry in document["array_keys"]}
    survey_objects = {entry["name"]: entry for entry in document["object_keys"]}
    for name in sorted(set(source_arrays) - set(survey_arrays)):
        problems.append("survey missing array key: " + name)
    for name in sorted(set(survey_arrays) - set(source_arrays)):
        problems.append("survey lists unregistered array key: " + name)
    for name in sorted(set(source_objects) - set(survey_objects)):
        problems.append("survey missing object key: " + name)
    for name in sorted(set(survey_objects) - set(source_objects)):
        problems.append("survey lists unregistered object key: " + name)
    for name in sorted(set(source_arrays) & set(survey_arrays)):
        source = source_arrays[name]
        survey = survey_arrays[name]
        if source["entry_count"] != survey["entry_count"]:
            problems.append("survey entry count drift for key: " + name
                            + " (source " + str(source["entry_count"])
                            + ", survey " + str(survey["entry_count"]) + ")")
        survey_fields = survey["fields"]
        for field in sorted(set(source["fields"]) - set(survey_fields)):
            problems.append("survey missing field: " + name + "." + field)
        for field in sorted(set(survey_fields) - set(source["fields"])):
            problems.append("survey lists unregistered field: " + name + "." + field)
        for field in sorted(set(source["fields"]) & set(survey_fields)):
            recomputed = source["fields"][field]
            recorded = survey_fields[field]
            if recomputed["presence_count"] != recorded["presence_count"]:
                problems.append("survey presence drift for field: "
                                + name + "." + field)
            if recomputed["types"] != recorded["types"]:
                problems.append("survey type drift for field: "
                                + name + "." + field
                                + " (source " + str(recomputed["types"])
                                + ", survey " + str(recorded["types"]) + ")")
            for metric in ("string_encoded_number_count",
                           "embedded_json_string_count",
                           "empty_string_count", "null_count"):
                if recomputed[metric] != recorded[metric]:
                    problems.append("survey " + metric + " drift for field: "
                                    + name + "." + field
                                    + " (source " + str(recomputed[metric])
                                    + ", survey " + str(recorded[metric]) + ")")
    for name in sorted(set(source_objects) & set(survey_objects)):
        source = source_objects[name]
        survey = survey_objects[name]
        if source["entry_count"] != survey["entry_count"]:
            problems.append("survey entry count drift for key: " + name
                            + " (source " + str(source["entry_count"])
                            + ", survey " + str(survey["entry_count"]) + ")")
        if source["value_types"] != survey["value_types"]:
            problems.append("survey value-shape drift for key: " + name
                            + " (source " + str(source["value_types"])
                            + ", survey " + str(survey["value_types"]) + ")")
    return problems


def check_readable_consistency(document, readable_text):
    problems = []
    for entry in document["array_keys"]:
        marker = "| `" + entry["name"] + "` | " + entry["encoding_class"] + " |"
        if marker not in readable_text:
            problems.append("readable missing array key row: " + entry["name"])
    for entry in document["object_keys"]:
        marker = "| `" + entry["name"] + "` | object |"
        if marker not in readable_text:
            problems.append("readable missing object key row: " + entry["name"])
    if "Observed encodings" not in readable_text:
        problems.append("readable missing observed-encodings labeling")
    if "Normalization" not in readable_text:
        problems.append("readable missing normalization labeling")
    if "mixed" not in readable_text:
        problems.append("readable missing mixed-encoding labeling")
    if NUMERIC_GRAMMAR not in readable_text:
        problems.append("readable missing numeric grammar")
    return problems


def compare_and_report(source_arrays, source_objects, source_whole,
                       document, readable_text):
    problems = []
    problems.extend(check_whole_file(source_whole, document))
    problems.extend(check_key_coverage(source_arrays, source_objects, document))
    problems.extend(check_readable_consistency(document, readable_text))
    report = {
        "schema_version": 1,
        "policy": "field-survey-verification-v1",
        "result": "agreement" if not problems else "drift",
        "array_keys": len(source_arrays),
        "object_keys": len(source_objects),
        "problems": problems,
    }
    return report


def build_argument_parser():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--repo-root", help="repository root to verify (default: current directory)")
    return parser


def run_verification(repo_root):
    root = Path(repo_root)
    if not root.is_dir():
        raise VerificationError("repository root invalid")
    document = load_survey(root / SURVEY_FILE)
    validate_source_references(document, root)
    readable_text = read_text_file(root / READABLE_FILE, "readable")
    config = load_main_config(root / MAIN_CONFIG_FILE)
    source_arrays, source_objects, source_whole = extract_survey(config)
    return compare_and_report(source_arrays, source_objects, source_whole,
                              document, readable_text)


def main(argv=None):
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    try:
        report = run_verification(args.repo_root or ".")
    except VerificationError as error:
        message = str(error)
        print(message, file=sys.stderr)
        return 2
    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    print(output, end="")
    return 0 if report["result"] == "agreement" else 1


if __name__ == "__main__":
    sys.exit(main())
