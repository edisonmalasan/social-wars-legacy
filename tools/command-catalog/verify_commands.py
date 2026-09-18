"""Offline read-only legacy command catalog verification.

Resolves the `cmd == "<name>"` dispatcher branches in the legacy command
module with inert AST analysis (string constants only) and checks the
reviewed catalog and readable inventory against them. Never imports or
executes the legacy application. Exit 0 agreement, 1 catalog drift,
2 invalid input or unsupported source syntax. Standard library only.
"""

import argparse
import ast
import json
from pathlib import Path
import sys

SOURCE_FILE = "command.py"
DISPATCH_FUNCTION = "do_command"
DISPATCH_VARIABLE = "cmd"
CATALOG_FILE = Path("docs") / "legacy-protocol" / "commands.json"
INVENTORY_FILE = Path("docs") / "legacy-protocol" / "commands.md"
MAX_SOURCE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_COMMANDS = 512
HANDLED = "handled"
FALLTHROUGH = "fallthrough"


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


def _test_mentions_cmd(node):
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and child.id == DISPATCH_VARIABLE:
            return True
    return False


def _literal_command_name(test):
    if not isinstance(test, ast.Compare):
        return None
    if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
        return None
    if not isinstance(test.left, ast.Name) or test.left.id != DISPATCH_VARIABLE:
        return None
    if len(test.comparators) != 1:
        return None
    comparator = test.comparators[0]
    if isinstance(comparator, ast.Constant) and isinstance(comparator.value, str):
        return comparator.value
    return None


def extract_command_branches(source_text):
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        raise VerificationError("source file not parseable")
    target = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == DISPATCH_FUNCTION:
            target = node
            break
    if target is None:
        raise VerificationError("unsupported dispatch syntax: do_command not found")
    branches = []
    for node in ast.walk(target):
        if not isinstance(node, ast.If):
            continue
        if not _test_mentions_cmd(node.test):
            continue
        name = _literal_command_name(node.test)
        if name is None:
            raise VerificationError("unsupported dispatch syntax: non-literal command comparison")
        if not name:
            raise VerificationError("unsupported dispatch syntax: empty command name")
        branches.append({"command": name, "line": node.lineno})
        if len(branches) > MAX_TOTAL_COMMANDS:
            raise VerificationError("command limit exceeded")
    seen = set()
    for branch in branches:
        if branch["command"] in seen:
            raise VerificationError("unsupported dispatch syntax: duplicate command branch")
        seen.add(branch["command"])
    return branches


def _require_string_list(value, what):
    if not isinstance(value, list) or not value:
        raise VerificationError("catalog schema invalid: " + what)
    for item in value:
        if not isinstance(item, str) or not item:
            raise VerificationError("catalog schema invalid: " + what)


def load_catalog(path):
    catalog = read_text_file(path, "catalog")
    try:
        document = json.loads(catalog)
    except ValueError:
        raise VerificationError("catalog file not valid json")
    if not isinstance(document, dict):
        raise VerificationError("catalog file not valid json")
    if document.get("schema_version") != 1:
        raise VerificationError("catalog schema invalid")
    policy = document.get("policy")
    if not isinstance(policy, dict):
        raise VerificationError("catalog schema invalid")
    for field in ("catalog_id", "source_file", "evidence_policy", "count_note"):
        if not isinstance(policy.get(field), str) or not policy[field]:
            raise VerificationError("catalog schema invalid: policy field " + field)
    for field in ("branch_count", "entry_count"):
        if type(policy.get(field)) is not int or policy[field] < 1:
            raise VerificationError("catalog schema invalid: policy field " + field)
    envelope = document.get("envelope")
    if not isinstance(envelope, dict):
        raise VerificationError("catalog schema invalid")
    for field in ("fields", "command_tuple", "resource_delta_shape"):
        _require_string_list(envelope.get(field), "envelope field " + field)
    for field in ("pre_dispatch", "batch_persistence", "fallthrough"):
        if not isinstance(envelope.get(field), str) or not envelope[field]:
            raise VerificationError("catalog schema invalid: envelope field " + field)
    envelope_refs = envelope.get("source_references")
    if not isinstance(envelope_refs, list) or not envelope_refs:
        raise VerificationError("catalog schema invalid: envelope source_references")
    entries = document.get("commands")
    if not isinstance(entries, list) or not entries:
        raise VerificationError("catalog schema invalid")
    seen = set()
    fallthrough_count = 0
    for entry in entries:
        if not isinstance(entry, dict):
            raise VerificationError("catalog schema invalid")
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            raise VerificationError("catalog schema invalid: entry name")
        if name in seen:
            raise VerificationError("catalog schema invalid: duplicate command")
        seen.add(name)
        classification = entry.get("classification")
        if classification not in (HANDLED, FALLTHROUGH):
            raise VerificationError("catalog schema invalid: classification " + name)
        if classification == FALLTHROUGH:
            fallthrough_count += 1
        for field in ("domain", "migration_status", "evidence"):
            if not isinstance(entry.get(field), str) or not entry[field]:
                raise VerificationError("catalog schema invalid: entry field " + field + " " + name)
        args = entry.get("args")
        if not isinstance(args, dict):
            raise VerificationError("catalog schema invalid: args " + name)
        positional = args.get("positional")
        if not isinstance(positional, list) or not all(isinstance(a, str) for a in positional):
            raise VerificationError("catalog schema invalid: args " + name)
        if not isinstance(args.get("shape"), str) or not args["shape"]:
            raise VerificationError("catalog schema invalid: args " + name)
        for field in ("resource_effects", "state_reads", "state_writes",
                      "persistence_effects", "client_trust", "security_notes"):
            _require_string_list(entry.get(field), "entry field " + field + " " + name)
        fixtures = entry.get("observed_fixtures")
        if not isinstance(fixtures, list) or not all(isinstance(f, str) and f for f in fixtures):
            raise VerificationError("catalog schema invalid: observed_fixtures " + name)
        references = entry.get("source_references")
        if not isinstance(references, list) or not references:
            raise VerificationError("catalog schema invalid: source_references " + name)
        for reference in references:
            if not isinstance(reference, dict) \
                    or not isinstance(reference.get("file"), str) or not reference["file"] \
                    or type(reference.get("line")) is not int or reference["line"] < 1 \
                    or type(reference.get("end_line")) is not int \
                    or reference["end_line"] < reference["line"]:
                raise VerificationError("catalog schema invalid: source reference " + name)
    if fallthrough_count != 1:
        raise VerificationError("catalog schema invalid: exactly one fallthrough entry required")
    if policy["entry_count"] != len(entries):
        raise VerificationError("catalog schema invalid: entry_count mismatch")
    if policy["branch_count"] != len([e for e in entries if e.get("classification") == HANDLED]):
        raise VerificationError("catalog schema invalid: branch_count mismatch")
    return document


def validate_source_references(document, root):
    try:
        anchored = root.resolve()
    except OSError:
        raise VerificationError("repository root invalid")
    blocks = [("envelope", document["envelope"].get("source_references", []))]
    for entry in document["commands"]:
        blocks.append((entry["name"], entry.get("source_references", [])))
    for label, references in blocks:
        for reference in references:
            name = reference.get("file")
            try:
                resolved = (root / name).resolve()
                resolved.relative_to(anchored)
            except (OSError, ValueError):
                raise VerificationError(
                    "catalog source reference outside repository: " + label)
            if not resolved.is_file():
                raise VerificationError(
                    "catalog source reference missing: " + label)
            content = read_text_file(resolved, "reference")
            total = len(content.splitlines())
            line = reference["line"]
            end_line = reference["end_line"]
            if not 1 <= line <= end_line <= total:
                raise VerificationError(
                    "catalog source reference out of range: " + label)


def handled_catalog_entries(document):
    return [entry for entry in document["commands"]
            if entry.get("classification") == HANDLED]


def check_command_coverage(branches, document):
    problems = []
    catalog_handled = handled_catalog_entries(document)
    source_names = [branch["command"] for branch in branches]
    catalog_names = [entry["name"] for entry in catalog_handled]
    for name in sorted(set(source_names) - set(catalog_names)):
        problems.append("catalog missing command branch: " + name)
    for name in sorted(set(catalog_names) - set(source_names)):
        problems.append("catalog lists unregistered command branch: " + name)
    return problems


def check_inventory_consistency(document, inventory_text):
    problems = []
    lowered = inventory_text.lower()
    for entry in document["commands"]:
        if entry["name"] not in inventory_text:
            problems.append("inventory missing command: " + entry["name"])
    if "time-manipulation" not in lowered:
        problems.append("inventory missing time-manipulation labeling")
    if "never a production" not in lowered:
        problems.append("inventory missing never-production labeling for debug and time paths")
    if "alliance" not in lowered or "not implemented" not in lowered:
        problems.append("inventory missing alliance placeholder labeling")
    if "apply_resources" not in inventory_text:
        problems.append("inventory missing pre-dispatch resource contract")
    return problems


def compare_and_report(branches, document, inventory_text):
    problems = []
    problems.extend(check_command_coverage(branches, document))
    problems.extend(check_inventory_consistency(document, inventory_text))
    report = {
        "schema_version": 1,
        "policy": "command-catalog-verification-v1",
        "result": "agreement" if not problems else "drift",
        "command_branches": len(branches),
        "catalog_commands": len(handled_catalog_entries(document)),
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
    source = read_text_file(root / SOURCE_FILE, "source")
    document = load_catalog(root / CATALOG_FILE)
    validate_source_references(document, root)
    inventory = read_text_file(root / INVENTORY_FILE, "inventory")
    branches = extract_command_branches(source)
    return compare_and_report(branches, document, inventory)


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
