"""Offline read-only legacy game-content census verification.

Compares the reviewed content census (`docs/game-content/census.json`) and
its readable inventory (`docs/game-content/census.md`) against the stored
content sources: `config/main.json`, the ordered patch list
`config/patch/patches.txt` with its patch files, and the mods pipeline
status in `mods/mods.txt`.

Only structural parsing with the standard library is used. The legacy
application is never imported, patches are parsed but never applied, served
(time-dependent) configuration is never produced, runtime saves are never
read, and no network, server, browser, or Flash activity occurs. Exit 0
agreement, 1 census drift, 2 invalid input or unsupported content shape.
Standard library only.
"""

import argparse
import json
from pathlib import Path
import sys

MAIN_CONFIG_FILE = Path("config") / "main.json"
PATCH_LIST_FILE = Path("config") / "patch" / "patches.txt"
PATCH_DIR = Path("config") / "patch"
MODS_LIST_FILE = Path("mods") / "mods.txt"
CENSUS_FILE = Path("docs") / "game-content" / "census.json"
INVENTORY_FILE = Path("docs") / "game-content" / "census.md"
MAX_SOURCE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_KEYS = 64
MAX_PATCH_FILES = 32
MAX_PATCH_OPS = 4096
SUPPORTED_OPS = ("add", "remove", "replace", "move", "copy", "test")


class VerificationError(Exception):
    pass


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


def parse_patch_list(text):
    """Return the ordered active patch names from patches.txt.

    Comment lines (starting with `#`) and blank lines are skipped, matching
    the legacy loader in `get_game_config.py`. A `.json` suffix is stripped,
    also matching the legacy loader.
    """
    names = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.endswith(".json"):
            stripped = stripped[:-len(".json")]
        if not stripped:
            raise VerificationError("unsupported patch list shape: empty patch name")
        names.append(stripped)
    if not names:
        raise VerificationError("unsupported patch list shape: no active patches")
    if len(names) > MAX_PATCH_FILES:
        raise VerificationError("patch limit exceeded")
    if len(set(names)) != len(names):
        raise VerificationError("unsupported patch list shape: duplicate patch name")
    return names


def parse_mods_list(text):
    """Return (active_mods, inactive_mods) from mods.txt.

    Active mods are non-comment, non-blank lines (with an optional `.json`
    suffix stripped), matching the legacy loader in `get_game_config.py`.
    Inactive mods are commented-out single-token lines such as
    `# no_hiring_needed`; prose comments (containing whitespace) are ignored.
    """
    active = []
    inactive = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            token = stripped[1:].strip()
            if token and not any(char.isspace() for char in token):
                token = token[:-len(".json")] if token.endswith(".json") else token
                inactive.append(token)
            continue
        name = stripped[:-len(".json")] if stripped.endswith(".json") else stripped
        if not name:
            raise VerificationError("unsupported mods list shape: empty mod name")
        active.append(name)
    if len(set(active)) != len(active):
        raise VerificationError("unsupported mods list shape: duplicate mod name")
    return active, inactive


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


def extract_key_inventory(document):
    inventory = []
    for key, value in document.items():
        shape = "array" if isinstance(value, list) else "object"
        inventory.append({"key": key, "container_shape": shape,
                          "entry_count": len(value)})
    return inventory


def normalize_patch_path(path):
    segments = path.split("/")
    normalized = [segment if not segment.isdigit() else "{index}"
                  for segment in segments]
    return "/".join(normalized)


def load_patch_file(path, name):
    text = read_text_file(path, "patch file " + name)
    try:
        operations = json.loads(text)
    except ValueError:
        raise VerificationError("patch file not valid json: " + name)
    if not isinstance(operations, list) or not operations:
        raise VerificationError("unsupported patch shape: " + name)
    if len(operations) > MAX_PATCH_OPS:
        raise VerificationError("patch operation limit exceeded: " + name)
    op_counts = {}
    targets = set()
    for operation in operations:
        if not isinstance(operation, dict):
            raise VerificationError("unsupported patch shape: " + name)
        op = operation.get("op")
        target = operation.get("path")
        if op not in SUPPORTED_OPS:
            raise VerificationError("unsupported patch operation: " + name)
        if not isinstance(target, str) or not target.startswith("/"):
            raise VerificationError("unsupported patch target path: " + name)
        op_counts[op] = op_counts.get(op, 0) + 1
        targets.add(normalize_patch_path(target))
    return {"name": name, "op_count": len(operations),
            "op_counts": op_counts, "target_paths": sorted(targets)}


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


def load_census(path):
    text = read_text_file(path, "census")
    try:
        document = json.loads(text)
    except ValueError:
        raise VerificationError("census file not valid json")
    if not isinstance(document, dict):
        raise VerificationError("census file not valid json")
    if document.get("schema_version") != 1:
        raise VerificationError("census schema invalid")
    policy = document.get("policy")
    if not isinstance(policy, dict):
        raise VerificationError("census schema invalid")
    for field in ("census_id", "source_file", "evidence_policy", "count_note",
                  "served_bytes_note"):
        if not _require_non_empty_string(policy.get(field)):
            raise VerificationError("census schema invalid: policy field " + field)
    for field in ("key_count", "patch_count"):
        if type(policy.get(field)) is not int or policy[field] < 1:
            raise VerificationError("census schema invalid: policy field " + field)
    entries = document.get("content_keys")
    if not isinstance(entries, list) or not entries:
        raise VerificationError("census schema invalid")
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise VerificationError("census schema invalid")
        name = entry.get("name")
        if not _require_non_empty_string(name):
            raise VerificationError("census schema invalid: entry name")
        if name in seen:
            raise VerificationError("census schema invalid: duplicate content key")
        seen.add(name)
        if entry.get("container_shape") not in ("array", "object"):
            raise VerificationError("census schema invalid: container_shape " + name)
        if type(entry.get("entry_count")) is not int or entry["entry_count"] < 0:
            raise VerificationError("census schema invalid: entry_count " + name)
        for field in ("id_scheme", "layering"):
            if not _require_non_empty_string(entry.get(field)):
                raise VerificationError(
                    "census schema invalid: entry field " + field + " " + name)
        asset_fields = entry.get("asset_reference_fields")
        if not isinstance(asset_fields, list) or not all(
                isinstance(item, str) for item in asset_fields):
            raise VerificationError(
                "census schema invalid: asset_reference_fields " + name)
        if not _require_source_references(entry.get("source_references")):
            raise VerificationError(
                "census schema invalid: source_references " + name)
    if policy["key_count"] != len(entries):
        raise VerificationError("census schema invalid: key_count mismatch")
    patches = document.get("patches")
    if not isinstance(patches, dict):
        raise VerificationError("census schema invalid")
    order = patches.get("order")
    if not isinstance(order, list) or not order or not all(
            _require_non_empty_string(item) for item in order):
        raise VerificationError("census schema invalid: patches order")
    if len(set(order)) != len(order):
        raise VerificationError("census schema invalid: duplicate patch name")
    if policy["patch_count"] != len(order):
        raise VerificationError("census schema invalid: patch_count mismatch")
    patch_entries = patches.get("entries")
    if not isinstance(patch_entries, list) or len(patch_entries) != len(order):
        raise VerificationError("census schema invalid: patches entries")
    seen_patches = set()
    for entry in patch_entries:
        if not isinstance(entry, dict):
            raise VerificationError("census schema invalid")
        name = entry.get("name")
        if not _require_non_empty_string(name):
            raise VerificationError("census schema invalid: patch entry name")
        if name in seen_patches:
            raise VerificationError("census schema invalid: duplicate patch entry")
        seen_patches.add(name)
        if type(entry.get("position")) is not int or entry["position"] < 1:
            raise VerificationError("census schema invalid: position " + name)
        if type(entry.get("op_count")) is not int or entry["op_count"] < 1:
            raise VerificationError("census schema invalid: op_count " + name)
        op_counts = entry.get("op_counts")
        if not isinstance(op_counts, dict) or not op_counts:
            raise VerificationError("census schema invalid: op_counts " + name)
        for op, count in op_counts.items():
            if op not in SUPPORTED_OPS or type(count) is not int or count < 1:
                raise VerificationError("census schema invalid: op_counts " + name)
        if sum(op_counts.values()) != entry["op_count"]:
            raise VerificationError("census schema invalid: op_counts total " + name)
        targets = entry.get("target_paths")
        if not isinstance(targets, list) or not targets or not all(
                _require_non_empty_string(item) for item in targets):
            raise VerificationError("census schema invalid: target_paths " + name)
        if not _require_source_references(entry.get("source_references")):
            raise VerificationError("census schema invalid: source_references " + name)
    if seen_patches != set(order):
        raise VerificationError("census schema invalid: patches order/entries mismatch")
    mods = document.get("mods")
    if not isinstance(mods, dict):
        raise VerificationError("census schema invalid")
    if not _require_non_empty_string(mods.get("status")):
        raise VerificationError("census schema invalid: mods status")
    for field in ("active_mods", "inactive_mods"):
        value = mods.get(field)
        if not isinstance(value, list) or not all(
                isinstance(item, str) for item in value):
            raise VerificationError("census schema invalid: mods field " + field)
    if not _require_source_references(mods.get("source_references")):
        raise VerificationError("census schema invalid: mods source_references")
    for section in ("duplicate_cleaning", "dynamic_derivation"):
        block = document.get(section)
        if not isinstance(block, dict):
            raise VerificationError("census schema invalid")
        if not _require_non_empty_string(block.get("description")):
            raise VerificationError("census schema invalid: " + section)
        if not _require_source_references(block.get("source_references")):
            raise VerificationError(
                "census schema invalid: source_references " + section)
    return document


def validate_source_references(document, root):
    try:
        anchored = root.resolve()
    except OSError:
        raise VerificationError("repository root invalid")
    blocks = []
    for entry in document["content_keys"]:
        blocks.append((entry["name"], entry.get("source_references", [])))
    for entry in document["patches"]["entries"]:
        blocks.append(("patch " + entry["name"], entry.get("source_references", [])))
    blocks.append(("mods", document["mods"].get("source_references", [])))
    blocks.append(("duplicate_cleaning",
                   document["duplicate_cleaning"].get("source_references", [])))
    blocks.append(("dynamic_derivation",
                   document["dynamic_derivation"].get("source_references", [])))
    for label, references in blocks:
        for reference in references:
            name = reference.get("file")
            try:
                resolved = (root / name).resolve()
                resolved.relative_to(anchored)
            except (OSError, ValueError):
                raise VerificationError(
                    "census source reference outside repository: " + label)
            if not resolved.is_file():
                raise VerificationError(
                    "census source reference missing: " + label)
            content = read_text_file(resolved, "reference")
            total = len(content.splitlines())
            line = reference["line"]
            end_line = reference["end_line"]
            if not 1 <= line <= end_line <= total:
                raise VerificationError(
                    "census source reference out of range: " + label)


def check_key_coverage(source_inventory, document):
    problems = []
    source_map = {item["key"]: item for item in source_inventory}
    census_map = {entry["name"]: entry for entry in document["content_keys"]}
    for name in sorted(set(source_map) - set(census_map)):
        problems.append("census missing content key: " + name)
    for name in sorted(set(census_map) - set(source_map)):
        problems.append("census lists unregistered content key: " + name)
    for name in sorted(set(source_map) & set(census_map)):
        source = source_map[name]
        census = census_map[name]
        if source["container_shape"] != census["container_shape"]:
            problems.append("census container shape drift for key: " + name)
        if source["entry_count"] != census["entry_count"]:
            problems.append("census entry count drift for key: " + name
                            + " (source " + str(source["entry_count"])
                            + ", census " + str(census["entry_count"]) + ")")
    return problems


def check_patch_coverage(source_order, source_patches, document):
    problems = []
    census_order = document["patches"]["order"]
    if source_order != census_order:
        problems.append("census patch order drift: source ["
                        + ", ".join(source_order) + "] vs census ["
                        + ", ".join(census_order) + "]")
    census_map = {entry["name"]: entry
                  for entry in document["patches"]["entries"]}
    source_map = {item["name"]: item for item in source_patches}
    for name in sorted(set(source_map) - set(census_map)):
        problems.append("census missing patch file: " + name)
    for name in sorted(set(census_map) - set(source_map)):
        problems.append("census lists unregistered patch file: " + name)
    for name in sorted(set(source_map) & set(census_map)):
        source = source_map[name]
        census = census_map[name]
        expected_position = source_order.index(name) + 1 if name in source_order else -1
        if census["position"] != expected_position:
            problems.append("census patch position drift: " + name)
        if source["op_count"] != census["op_count"]:
            problems.append("census patch op count drift: " + name
                            + " (source " + str(source["op_count"])
                            + ", census " + str(census["op_count"]) + ")")
        if source["op_counts"] != census["op_counts"]:
            problems.append("census patch op mix drift: " + name)
        if source["target_paths"] != census["target_paths"]:
            problems.append("census patch target drift: " + name)
    return problems


def check_mods_coverage(source_active, source_inactive, document):
    problems = []
    mods = document["mods"]
    if source_active != mods["active_mods"]:
        problems.append("census mods status drift: source active ["
                        + ", ".join(source_active) + "] vs census active ["
                        + ", ".join(mods["active_mods"]) + "]")
    if source_inactive != mods["inactive_mods"]:
        problems.append("census mods status drift: source inactive ["
                        + ", ".join(source_inactive) + "] vs census inactive ["
                        + ", ".join(mods["inactive_mods"]) + "]")
    return problems


def check_inventory_consistency(document, inventory_text):
    problems = []
    for entry in document["content_keys"]:
        if entry["name"] not in inventory_text:
            problems.append("inventory missing content key: " + entry["name"])
    for name in document["patches"]["order"]:
        if name not in inventory_text:
            problems.append("inventory missing patch: " + name)
    lowered = inventory_text.lower()
    if "inactive" not in lowered or "mods" not in lowered:
        problems.append("inventory missing inactive mods pipeline labeling")
    if "stored" not in lowered or "served" not in lowered:
        problems.append("inventory missing stored versus served labeling")
    if "make_dynamic" not in inventory_text:
        problems.append("inventory missing make_dynamic derivation boundary")
    if "remove_duplicate_items" not in inventory_text:
        problems.append("inventory missing remove_duplicate_items labeling")
    return problems


def compare_and_report(source_inventory, source_order, source_patches,
                       source_active, source_inactive, document, inventory_text):
    problems = []
    problems.extend(check_key_coverage(source_inventory, document))
    problems.extend(check_patch_coverage(source_order, source_patches, document))
    problems.extend(check_mods_coverage(source_active, source_inactive, document))
    problems.extend(check_inventory_consistency(document, inventory_text))
    report = {
        "schema_version": 1,
        "policy": "content-census-verification-v1",
        "result": "agreement" if not problems else "drift",
        "content_keys": len(source_inventory),
        "patch_files": len(source_order),
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
    document = load_census(root / CENSUS_FILE)
    validate_source_references(document, root)
    inventory_text = read_text_file(root / INVENTORY_FILE, "inventory")
    config = load_main_config(root / MAIN_CONFIG_FILE)
    source_inventory = extract_key_inventory(config)
    patch_names = parse_patch_list(read_text_file(root / PATCH_LIST_FILE, "patch list"))
    source_patches = [load_patch_file(root / PATCH_DIR / (name + ".json"), name)
                      for name in patch_names]
    mods_text = read_text_file(root / MODS_LIST_FILE, "mods list")
    source_active, source_inactive = parse_mods_list(mods_text)
    return compare_and_report(source_inventory, patch_names, source_patches,
                              source_active, source_inactive,
                              document, inventory_text)


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
